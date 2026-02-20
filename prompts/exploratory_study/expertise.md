You are a network security expert. Your task is to analyze the following NIDS alert and determine if it represents a malicious attack or a false positive.

Expert Knowledge for '{alert_type}':
{advice}

Input Alert:
{alert_str}

Directly classify the alert based on the information provided and the expert knowledge. DO NOT include any thinking process or reasoning explanation.
Respond with a JSON object containing ONLY:
- "classification": "True Positive" or "False Positive"
- "confidence": A score between 0 and 100
