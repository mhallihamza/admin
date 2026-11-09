function flowSecurityGate() {
  const chat = node("ChatInput", "Request Payload (JSON)", { x: col(0), y: 0 },
    { input_value: '{"text": "Comment renouveler ma carte ?", "request_type": "chat", "user_id": "u-1", "roles": ["CITIZEN"], "disabled": false, "filename": null, "source_user_id": null, "agent": null, "tool": null, "agent_tool_allowed": true}' },
    { suffix: "s0" });
  const toMsg = node("TypeConverterComponent", "Payload to Message", { x: col(1), y: 0 }, { output_type: "Message" }, { suffix: "s1" });
  const layer1 = replStep("s2", "Layer 1 Rules", "layer1_rules.template.py", "json,re,ast", col(2), 0,
    { vars: { context: [toMsg, "message_output"] } });
  const extract = replStep("s3", "Extract Text For Detection", "extract_text_for_detection.template.py", "json,re,ast", col(2), 300,
    { vars: { context: [toMsg, "message_output"] } });
  const toMsgL2 = node("TypeConverterComponent", "Text to Message", { x: col(4), y: 300 }, { output_type: "Message" }, { suffix: "s4c" });
  const detector = node("MistralModel", "Layer 2 Detector (plain model)", { x: col(5), y: 300 },
    { model_name: "codestral-latest", temperature: 0, input_value: "", api_key: "", timeout: 30, system_message: loadCode("layer2_detector_system_message.txt") }, { suffix: "s4" });
  const toMsg2 = node("TypeConverterComponent", "Layer1 to Message", { x: col(3), y: 120 }, { output_type: "Message" }, { suffix: "s7" });
  const merge = replStep("s5", "Central Decision (fixed code)", "gate_merge.template.py", "json,re,ast", col(6), 0,
    { vars: { layer1_json: [toMsg2, "message_output"], layer2_text: [detector, "text_output"], session_json: [toMsg, "message_output"] } });
  const toMsgDec = node("TypeConverterComponent", "Decision to Message", { x: col(8), y: 120 }, { output_type: "Message" }, { suffix: "s9" });

  // Deterministic conditional-router chain — no LLM in routing
  const routerAllow = node("ConditionalRouter", "Route ALLOW", { x: col(9), y: 0 },
    { operator: "contains", match_text: '"decision": "ALLOW"', case_sensitive: true, input_text: "", true_case_message: "", false_case_message: "", default_route: "false_result" }, { suffix: "r1" });
  const routerReview = node("ConditionalRouter", "Route REVIEW", { x: col(10), y: 280 },
    { operator: "contains", match_text: '"decision": "REVIEW"', case_sensitive: true, input_text: "", true_case_message: "", false_case_message: "", default_route: "false_result" }, { suffix: "r2" });
  const routerRestrict = node("ConditionalRouter", "Route RESTRICT", { x: col(11), y: 280 },
    { operator: "contains", match_text: '"decision": "RESTRICT"', case_sensitive: true, input_text: "", true_case_message: "", false_case_message: "", default_route: "false_result" }, { suffix: "r3" });

  // ALLOW route — carries the full payload for the next workflow
  const gateOut = node("ChatOutput", "Gate Result (payload for next workflow)", { x: col(12), y: 0 }, {}, { suffix: "g1" });

  // REVIEW route — log and hold
  const revLog = replStep("v1", "Log Review Hold", "log_security_incident.template.py", "json,re,urllib.request,urllib.error", col(12), 280,
    { vars: { context: [routerReview, "true_result"] } });
  const revTc = node("TypeConverterComponent", "Review to Message", { x: col(14), y: 280 }, { output_type: "Message" }, { suffix: "v2" });
  const revOut = node("ChatOutput", "Review Hold", { x: col(15), y: 280 }, {}, { suffix: "v3" });

  // RESTRICT route — log and hold
  const resLog = replStep("x1", "Log Restricted", "log_security_incident.template.py", "json,re,urllib.request,urllib.error", col(12), 560,
    { vars: { context: [routerRestrict, "true_result"] } });
  const resTc = node("TypeConverterComponent", "Restricted to Message", { x: col(14), y: 560 }, { output_type: "Message" }, { suffix: "x2" });
  const resOut = node("ChatOutput", "Restricted (held)", { x: col(15), y: 560 }, {}, { suffix: "x3" });

  // BLOCK route — log incident and stop
  const blkLog = replStep("b1", "Log Blocked Incident", "log_security_incident.template.py", "json,re,urllib.request,urllib.error", col(14), 840,
    { vars: { context: [routerRestrict, "false_result"] } });
  const blkTc = node("TypeConverterComponent", "Blocked to Message", { x: col(16), y: 840 }, { output_type: "Message" }, { suffix: "b2" });
  const blkOut = node("ChatOutput", "Blocked", { x: col(17), y: 840 }, {}, { suffix: "b3" });

  const edges = [
    edge(chat, "message", toMsg, "input_data"),
    ...layer1.connections,
    layer1.internal,
    ...extract.connections,
    extract.internal,
    edge(extract.interpreter, "results", toMsgL2, "input_data"),
    edge(toMsgL2, "message_output", detector, "input_value"),
    edge(layer1.interpreter, "results", toMsg2, "input_data"),
    ...merge.connections,
    merge.internal,
    edge(merge.interpreter, "results", toMsgDec, "input_data"),
    // routers read the decision message
    edge(toMsgDec, "message_output", routerAllow, "input_text"),
    edge(toMsgDec, "message_output", routerReview, "input_text"),
    edge(toMsgDec, "message_output", routerRestrict, "input_text"),
    // ALLOW
    edge(routerAllow, "true_result", gateOut, "input_value"),
    // REVIEW
    edge(routerReview, "true_result", revLog.wrapper, "context"),
    ...revLog.connections,
    revLog.internal,
    edge(revLog.interpreter, "results", revTc, "input_data"),
    edge(revTc, "message_output", revOut, "input_value"),
    // RESTRICT
    edge(routerRestrict, "true_result", resLog.wrapper, "context"),
    ...resLog.connections,
    resLog.internal,
    edge(resLog.interpreter, "results", resTc, "input_data"),
    edge(resTc, "message_output", resOut, "input_value"),
    // BLOCK (Router 3 false = not RESTRICT = BLOCK or unknown)
    edge(routerRestrict, "false_result", blkLog.wrapper, "context"),
    ...blkLog.connections,
    blkLog.internal,
    edge(blkLog.interpreter, "results", blkTc, "input_data"),
    edge(blkTc, "message_output", blkOut, "input_value"),
  ];

  return buildFlow(
    "01 - Central Security Gate",
    "SECURITY ONLY. Linear fail-closed pipeline with deterministic conditional-router chain. Layer 1 rules + Layer 2 detection + Central Decision (fixed code, model never decides) + Smart routing (ALLOW passes the full payload; REVIEW held; RESTRICT held; BLOCK logged and stopped; unknown falls to BLOCK).",
    [chat, toMsg, layer1.wrapper, layer1.interpreter, extract.wrapper, extract.interpreter, toMsgL2, detector, toMsg2, merge.wrapper, merge.interpreter, toMsgDec, routerAllow, gateOut, routerReview, revLog.wrapper, revLog.interpreter, revTc, revOut, routerRestrict, resLog.wrapper, resLog.interpreter, resTc, resOut, blkLog.wrapper, blkLog.interpreter, blkTc, blkOut],
    edges
  );
}