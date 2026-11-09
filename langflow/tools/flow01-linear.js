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
  const logStop = replStep("s6", "Log and Gate", "log_security_incident.template.py", "json,re,ast,urllib.request,urllib.error", col(8), 280,
    { vars: { context: [toMsgDec, "message_output"] } });
  const gateTc = node("TypeConverterComponent", "Gate Result to Message", { x: col(10), y: 120 }, { output_type: "Message" }, { suffix: "s10" });
  const gateOut = node("ChatOutput", "Gate Result (payload for the next workflow)", { x: col(11), y: 0 }, {}, { suffix: "s11" });

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
    ...logStop.connections,
    logStop.internal,
    edge(logStop.interpreter, "results", gateTc, "input_data"),
    edge(gateTc, "message_output", gateOut, "input_value"),
  ];

  return buildFlow(
    "01 - Central Security Gate",
    "SECURITY ONLY. Linear fail-closed pipeline: Layer 1 rules + Layer 2 detection + Central Decision (fixed code, model never decides) + Log/Gate step (ALLOW passes the full payload; non-ALLOW logs to DB and raises, stopping the workflow).",
    [chat, toMsg, layer1.wrapper, layer1.interpreter, extract.wrapper, extract.interpreter, toMsgL2, detector, toMsg2, merge.wrapper, merge.interpreter, toMsgDec, logStop.wrapper, logStop.interpreter, gateTc, gateOut],
    edges
  );
}