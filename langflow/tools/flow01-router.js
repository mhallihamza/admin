function flowSecurityGate() {
  const chat = node("ChatInput", "Request Payload (JSON)", { x: col(0), y: 0 },
    { input_value: '{"text": "Comment renouveler ma carte ?", "request_type": "chat", "user_id": "u-1", "roles": ["CITIZEN"], "disabled": false, "filename": null, "source_user_id": null, "agent": null, "tool": null, "agent_tool_allowed": true}' },
    { suffix: "s0" });
  const toMsg = node("TypeConverterComponent", "Payload → Message", { x: col(1), y: 0 }, { output_type: "Message" }, { suffix: "s1" });
  const layer1 = replStep("s2", "Layer 1 Rules", "layer1_rules.template.py", "json,re,ast", col(2), 0,
    { vars: { context: [toMsg, "message_output"] } });
  const extract = replStep("s3", "Extract Text For Detection", "extract_text_for_detection.template.py", "json,re,ast", col(2), 300,
    { vars: { context: [toMsg, "message_output"] } });
  const toMsgL2 = node("TypeConverterComponent", "Text → Message", { x: col(4), y: 300 }, { output_type: "Message" }, { suffix: "s4c" });
  const detector = node("MistralModel", "Layer 2 Detector (plain model)", { x: col(5), y: 300 },
    { model_name: "mistral-small-latest", temperature: 0, input_value: "", api_key: "", timeout: 30, system_message: loadCode("layer2_detector_system_message.txt") }, { suffix: "s4" });
  const toMsg2 = node("TypeConverterComponent", "Layer1 → Message", { x: col(3), y: 120 }, { output_type: "Message" }, { suffix: "s7" });
  const merge = replStep("s5", "Central Decision (fixed code)", "gate_merge.template.py", "json,re,ast", col(6), 0,
    { vars: { layer1_json: [toMsg2, "message_output"], layer2_text: [detector, "text_output"], session_json: [toMsg, "message_output"] } });
  const toMsgDec = node("TypeConverterComponent", "Decision → Message", { x: col(8), y: 120 }, { output_type: "Message" }, { suffix: "s9" });

  // Deterministic conditional-router chain (NO LLM in routing). Each router
  // excludes the untaken branch's downstream execution natively
  // (exclude_branch_conditionally). Unknown decisions fall through to BLOCK.
  const routerAllow = node("ConditionalRouter", "Route 1 — ALLOW ?", { x: col(10), y: 0 },
    { operator: "starts with", match_text: "GATE_DECISION: ALLOW", case_sensitive: true, input_text: "", true_case_message: "", false_case_message: "", default_route: "false_result" }, { suffix: "r1" });
  const routerReview = node("ConditionalRouter", "Route 2 — REVIEW ?", { x: col(12), y: 280 },
    { operator: "starts with", match_text: "GATE_DECISION: REVIEW", case_sensitive: true, input_text: "", true_case_message: "", false_case_message: "", default_route: "false_result" }, { suffix: "r2" });
  const routerRestrict = node("ConditionalRouter", "Route 3 — RESTRICT ?", { x: col(14), y: 280 },
    { operator: "starts with", match_text: "GATE_DECISION: RESTRICT", case_sensitive: true, input_text: "", true_case_message: "", false_case_message: "", default_route: "false_result" }, { suffix: "r3" });

  // ALLOW route — the only path to Gate Result (carries decision + session)
  const gateTc = node("TypeConverterComponent", "ALLOW Payload → Message", { x: col(12), y: 0 }, { output_type: "Message" }, { suffix: "g1" });
  const gateOut = node("ChatOutput", "Gate Result (payload for the next workflow)", { x: col(13), y: 0 }, {}, { suffix: "g2" });

  // REVIEW route — log to DB and hold for manual review
  const review = replStep("v1", "Log Review Hold", "log_security_incident.template.py", "json,re,urllib.request,urllib.error", col(14), 280,
    { vars: { context: [routerReview, "true_result"] } });
  const reviewTc = node("TypeConverterComponent", "Review → Message", { x: col(16), y: 280 }, { output_type: "Message" }, { suffix: "v2" });
  const reviewOut = node("ChatOutput", "Review Hold (manual review required)", { x: col(17), y: 280 }, {}, { suffix: "v3" });

  // RESTRICT route — log to DB and stop (restricted continuation is a future integration)
  const restrict = replStep("x1", "Log Restricted", "log_security_incident.template.py", "json,re,urllib.request,urllib.error", col(16), 560,
    { vars: { context: [routerRestrict, "true_result"] } });
  const restrictTc = node("TypeConverterComponent", "Restricted → Message", { x: col(18), y: 560 }, { output_type: "Message" }, { suffix: "x2" });
  const restrictOut = node("ChatOutput", "Restricted (held)", { x: col(19), y: 560 }, {}, { suffix: "x3" });

  // BLOCK route — log incident to DB and stop
  const block = replStep("b1", "Log Blocked Incident", "log_security_incident.template.py", "json,re,urllib.request,urllib.error", col(16), 840,
    { vars: { context: [routerRestrict, "false_result"] } });
  const blockTc = node("TypeConverterComponent", "Blocked → Message", { x: col(18), y: 840 }, { output_type: "Message" }, { suffix: "b2" });
  const blockOut = node("ChatOutput", "Blocked", { x: col(19), y: 840 }, {}, { suffix: "b3" });

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
    // every router reads the same decision message
    edge(toMsgDec, "message_output", routerAllow, "input_text"),
    edge(toMsgDec, "message_output", routerAllow, "true_case_message"),
    edge(toMsgDec, "message_output", routerAllow, "false_case_message"),
    edge(toMsgDec, "message_output", routerReview, "input_text"),
    edge(toMsgDec, "message_output", routerReview, "true_case_message"),
    edge(toMsgDec, "message_output", routerReview, "false_case_message"),
    edge(toMsgDec, "message_output", routerRestrict, "input_text"),
    edge(toMsgDec, "message_output", routerRestrict, "true_case_message"),
    edge(toMsgDec, "message_output", routerRestrict, "false_case_message"),
    // ALLOW — the only route to Gate Result
    edge(routerAllow, "true_result", gateTc, "input_data"),
    edge(gateTc, "message_output", gateOut, "input_value"),
    // REVIEW — log and hold
    edge(routerReview, "true_result", review.wrapper, "context"),
    ...review.connections,
    review.internal,
    edge(review.interpreter, "results", reviewTc, "input_data"),
    edge(reviewTc, "message_output", reviewOut, "input_value"),
    // RESTRICT — log and stop
    edge(routerRestrict, "true_result", restrict.wrapper, "context"),
    ...restrict.connections,
    restrict.internal,
    edge(restrict.interpreter, "results", restrictTc, "input_data"),
    edge(restrictTc, "message_output", restrictOut, "input_value"),
    // BLOCK — log incident and stop
    edge(routerRestrict, "false_result", block.wrapper, "context"),
    ...block.connections,
    block.internal,
    edge(block.interpreter, "results", blockTc, "input_data"),
    edge(blockTc, "message_output", blockOut, "input_value"),
  ];

  return buildFlow(
    "01 - Central Security Gate",
    "SECURITY ONLY. Entry workflow: Layer 1 fixed Python rules + Layer 2 detection (plain model, sees only the user text). Central Decision computes the decision deterministically (the model never decides) and a chain of conditional routers routes it: ALLOW → Gate Result (payload for the next workflow); REVIEW/RESTRICT/BLOCK → logged directly to the database and stopped; unknown → BLOCK. The Layer 2 model is a plain model node — structurally incapable of calling tools — and never sees roles/ids/permission flags.",
    [chat, toMsg, layer1.wrapper, layer1.interpreter, extract.wrapper, extract.interpreter, toMsgL2, detector, toMsg2, merge.wrapper, merge.interpreter, toMsgDec, routerAllow, gateTc, gateOut, routerReview, review.wrapper, review.interpreter, reviewTc, reviewOut, routerRestrict, restrict.wrapper, restrict.interpreter, restrictTc, restrictOut, block.wrapper, block.interpreter, blockTc, blockOut],
    edges
  );
}