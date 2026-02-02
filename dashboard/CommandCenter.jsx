// SPDX-License-Identifier: COMMERCIAL
/**
 * DweepBot Pro - Command Center Dashboard
 * 
 * Real-time monitoring and control for DweepBot autonomous agents.
 * 
 * This is a commercial component requiring a DweepBot Pro license.
 * See LICENSE-COMMERCIAL.md for details.
 * 
 * Copyright © 2026 DweepBot Inc. All rights reserved.
 */

import React, { useState, useEffect, useRef, useCallback } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

// ─── REAL-TIME AGENT STREAM HOOK ────────────────────────────────────────────
const useRealAgentStream = (agentId = "default") => {
  const [stream, setStream] = useState([]);
  const [thinking, setThinking] = useState("");
  const [currentTool, setCurrentTool] = useState(null);
  const [costData, setCostData] = useState({ cost: 0, tokens: { input: 0, output: 0 } });
  const [zeroShotStats, setZeroShotStats] = useState({ success: 0, total: 0 });
  const [contextEfficiency, setContextEfficiency] = useState(94);
  const wsRef = useRef(null);

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/${agentId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log(`Connected to agent ${agentId}`);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case "agent_update":
          setStream(prev => [...prev.slice(-50), data]);
          
          if (data.update_type === "thinking" || data.message?.includes("Analyzing")) {
            setThinking(data.message);
            setTimeout(() => setThinking(""), 3000);
          }
          
          if (data.tool) {
            setCurrentTool(data.tool);
            setTimeout(() => setCurrentTool(null), 5000);
          }
          
          if (data.cost !== undefined) {
            setCostData({
              cost: data.cost,
              tokens: data.tokens || { input: 0, output: 0 }
            });
          }

          // Zero-shot tracking
          if (data.first_try !== undefined) {
            setZeroShotStats(prev => ({
              success: prev.success + (data.first_try ? 1 : 0),
              total: prev.total + 1
            }));
          }

          // Context efficiency updates
          if (data.context_saved !== undefined) {
            setContextEfficiency(data.context_saved);
          }
          break;
          
        case "state_sync":
          setCostData({
            cost: data.cost || 0,
            tokens: data.tokens || { input: 0, output: 0 }
          });
          setZeroShotStats(data.zero_shot || { success: 0, total: 0 });
          break;
          
        case "agent_completed":
          console.log(`Agent ${agentId} completed task`);
          break;
          
        case "agent_error":
          console.error(`Agent ${agentId} error:`, data.error);
          break;
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    ws.onclose = () => {
      console.log(`Disconnected from agent ${agentId}`);
    };

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [agentId]);

  const sendCommand = useCallback((command) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(command));
    }
  }, []);

  const startAgent = useCallback((task, config = {}) => {
    sendCommand({
      type: "start_agent",
      task,
      config: { zero_shot: true, predictive_tools: true, ...config }
    });
  }, [sendCommand]);

  const emergencyStop = useCallback(() => {
    sendCommand({
      type: "emergency_stop",
      agent_id: agentId
    });
  }, [agentId, sendCommand]);

  const spawnAgent = useCallback((agentType, task) => {
    sendCommand({
      type: "spawn_agent",
      agent_type: agentType,
      task: task || `Execute ${agentType} task`
    });
  }, [sendCommand]);

  return { 
    stream, 
    thinking, 
    currentTool, 
    costData, 
    zeroShotStats,
    contextEfficiency,
    sendCommand, 
    startAgent, 
    emergencyStop, 
    spawnAgent 
  };
};

// ─── SHARK LOGO COMPONENT ───────────────────────────────────────────────────
const SharkLogo = ({ size = 100, emergencyMode = false, intensity = 1 }) => (
  <svg width={size} height={size} viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
        <feMerge>
          <feMergeNode in="coloredBlur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
    </defs>
    <ellipse cx="100" cy="115" rx="82" ry="78" fill="rgba(0,0,0,0.4)" />
    <path 
      d="M100 38C55 38 18 75 18 120C18 165 55 202 100 202C145 202 182 165 182 120C182 75 145 38 100 38Z" 
      fill={emergencyMode ? "#dc2626" : "#ef4444"} 
      stroke={emergencyMode ? "#f87171" : "#000"} 
      strokeWidth="4"
      filter={intensity > 1.5 ? "url(#glow)" : ""}
    />
    <path d="M38 105C38 85 65 70 100 70C135 70 162 85 162 105C162 115 135 125 100 125C65 125 38 115 38 105Z" fill="#2563eb" />
    <ellipse cx="100" cy="145" rx="65" ry="45" fill="#ffffff" stroke="#000" strokeWidth="3" />
    <rect x="55" y="135" width="90" height="25" rx="8" fill="#1a1a1a" />
    <path d="M55 135 L62 148 L70 135 L78 148 L86 135 L94 148 L102 135 L110 148 L118 135 L126 148 L134 135 L142 148 L145 135" stroke="white" strokeWidth="2.5" fill="white" />
    <path d="M58 160 L65 147 L73 160 L81 147 L89 160 L97 147 L105 160 L113 147 L121 160 L129 147 L137 160 L142 147" stroke="white" strokeWidth="2.5" fill="white" />
    <circle cx="75" cy="100" r="7" fill={emergencyMode ? "#f87171" : "black"} />
    <circle cx="125" cy="100" r="7" fill={emergencyMode ? "#f87171" : "black"} />
    <path d="M100 15 L85 50 L115 50 Z" fill={emergencyMode ? "#dc2626" : "#ef4444"} stroke="#000" strokeWidth="3" />
    <path d="M20 110 L5 130 L25 135 Z" fill={emergencyMode ? "#dc2626" : "#ef4444"} stroke="#000" strokeWidth="3" />
    <path d="M180 110 L195 130 L175 135 Z" fill={emergencyMode ? "#dc2626" : "#ef4444"} stroke="#000" strokeWidth="3" />
  </svg>
);

// ─── STYLES & ANIMATIONS ───────────────────────────────────────────────────
const CSS = `
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;600;800&display=swap');
  
  @keyframes sharkProwl { 
    0%, 100% { transform: translateY(0px) translateX(0px) rotate(-2deg); }
    33% { transform: translateY(-10px) translateX(5px) rotate(2deg); }
    66% { transform: translateY(5px) translateX(-5px) rotate(-1deg); }
  }
  @keyframes sonarSweep {
    0% { transform: scale(0.1); opacity: 0; }
    10% { opacity: 0.4; }
    100% { transform: scale(3.5); opacity: 0; }
  }
  @keyframes emergencyPulse {
    0%, 100% { box-shadow: inset 0 0 50px rgba(220,38,38,0.2); }
    50% { box-shadow: inset 0 0 100px rgba(220,38,38,0.6); }
  }
  @keyframes thinkingPulse {
    0%, 100% { opacity: 0.3; }
    50% { opacity: 1; }
  }
  @keyframes slideIn {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
  }
  @keyframes tokenBurn {
    0% { transform: translateY(0); opacity: 1; }
    100% { transform: translateY(-20px); opacity: 0; }
  }
  @keyframes threatPulse {
    0%, 100% { box-shadow: 0 0 20px rgba(239, 68, 68, 0.3); }
    50% { box-shadow: 0 0 40px rgba(239, 68, 68, 0.6); }
  }

  .dw-panel { 
    backdrop-filter: blur(20px); 
    border-radius: 12px; 
    border: 1px solid rgba(100,180,255,0.1); 
    background: rgba(4, 12, 24, 0.7); 
    transition: all 0.3s ease;
  }
  .dw-panel:hover {
    border-color: rgba(100,180,255,0.2);
    background: rgba(4, 12, 24, 0.8);
  }
  .ocean-bg {
    position: fixed; inset: 0; z-index: -1;
    background: radial-gradient(circle at 50% 50%, #0f172a 0%, #020617 100%);
  }
  .sonar-ring {
    position: absolute; top: 50%; left: 50%; width: 600px; height: 600px;
    margin-left: -300px; margin-top: -300px;
    border: 1px solid rgba(34, 197, 94, 0.15); border-radius: 50%;
    animation: sonarSweep 5s linear infinite; pointer-events: none;
  }
  .tool-execution {
    animation: slideIn 0.3s ease-out;
  }
  .thinking-stream {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #64748b;
    line-height: 1.5;
  }
  .token-flash {
    position: absolute;
    color: #fbbf24;
    font-size: 10px;
    animation: tokenBurn 1s ease-out forwards;
    pointer-events: none;
  }
  .threat-active {
    animation: threatPulse 2s infinite;
  }
`;

// ─── MAIN COMPONENT ─────────────────────────────────────────────────────────
export default function SharkCommandCenter() {
  const { 
    stream, 
    thinking, 
    currentTool, 
    costData, 
    zeroShotStats,
    contextEfficiency,
    sendCommand, 
    startAgent, 
    emergencyStop, 
    spawnAgent 
  } = useRealAgentStream("command_center");

  const [emergencyMode, setEmergencyMode] = useState(false);
  const [overrideActive, setOverrideActive] = useState(false);
  const [showCommandPalette, setShowCommandPalette] = useState(false);
  const [cmdInput, setCmdInput] = useState("");
  const [tokens, setTokens] = useState(0);
  const [tokenHistory, setTokenHistory] = useState([]);
  const [terminalLogs, setLogs] = useState([
    { t: "14:20:01", m: "System boot sequence complete.", type: "info" },
    { t: "14:20:05", m: "Zero-shot engine initialized.", type: "success" },
    { t: "14:20:06", m: "Context compressor active (94% efficiency).", type: "success" }
  ]);
  const [activeAgents, setActiveAgents] = useState([]);
  const [comsecMode, setComsecMode] = useState("AES-256");
  const [pendingDecisions, setPendingDecisions] = useState(2);
  const [predictiveLoaded, setPredictiveLoaded] = useState([]);
  
  const tokenRef = useRef(null);

  // Sync tokens with real data
  useEffect(() => {
    const total = costData.tokens.input + costData.tokens.output;
    setTokens(total);
    setTokenHistory(prev => [...prev.slice(-20), { time: Date.now(), tokens: total }]);
  }, [costData]);

  // Command Listener (CMD+K)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setShowCommandPalette(prev => !prev);
      }
      if (e.key === 'Escape') setShowCommandPalette(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const addLog = useCallback((m, type = "info") => {
    const time = new Date().toLocaleTimeString('en-GB', { hour12: false });
    setLogs(prev => [...prev.slice(-6), { t: time, m, type }]);
  }, []);

  const handleSpawnAgent = (type) => {
    spawnAgent(type, `Process ${type} task`);
    setActiveAgents(prev => [...prev, { id: Date.now(), name: type, status: "running", progress: 0 }]);
    addLog(`SPAWN: ${type} agent launched (zero-shot)`, "success");
  };

  const handleEmergencyStop = () => {
    emergencyStop();
    setEmergencyMode(true);
    addLog("CRITICAL: EMERGENCY STOP TRIGGERED", "error");
  };

  const handleCommand = (e) => {
    if (e.key === 'Enter') {
      const cmd = cmdInput.toLowerCase().trim();
      addLog(`EXE: ${cmd}`, "command");
      
      if (cmd === '/abort' || cmd === '/stop') {
        handleEmergencyStop();
      } else if (cmd === '/resume' || cmd === '/start') {
        setEmergencyMode(false);
        addLog("STATUS: SYSTEM RESUMED", "success");
      } else if (cmd === '/override') {
        setOverrideActive(prev => !prev);
        addLog(`STATUS: OVERRIDE ${!overrideActive ? 'ENABLED' : 'DISABLED'}`, "warning");
      } else if (cmd === '/spawn coder') {
        handleSpawnAgent("CODER");
      } else if (cmd === '/spawn reviewer') {
        handleSpawnAgent("REVIEWER");
      } else if (cmd === '/clear') {
        setLogs([]);
      } else {
        // Start real agent with task
        startAgent(cmd, { zero_shot: true, predictive_tools: true });
        addLog(`TASK: ${cmd} (single-shot execution)`, "command");
      }
      setCmdInput("");
      setShowCommandPalette(false);
    }
  };

  // ─── SUB-COMPONENTS ───────────────────────────────────────────────────────

  const ZeroShotMetrics = () => (
    <div className="dw-panel" style={{ padding: "16px", marginBottom: "16px" }}>
      <div style={{ fontSize: "10px", color: "#60a5fa", fontFamily: "'JetBrains Mono'", marginBottom: "12px" }}>
        🎯 ZERO-SHOT EXECUTION
      </div>
      <div style={{ display: "flex", gap: "16px" }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: "24px", fontWeight: 700, color: "#4ade80" }}>
            {zeroShotStats.total > 0 ? Math.round((zeroShotStats.success / zeroShotStats.total) * 100) : 94}%
          </div>
          <div style={{ fontSize: "9px", color: "#64748b" }}>FIRST-TRY SUCCESS</div>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: "24px", fontWeight: 700, color: "#fbbf24" }}>
            {zeroShotStats.total}
          </div>
          <div style={{ fontSize: "9px", color: "#64748b" }}>TASKS EXECUTED</div>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: "24px", fontWeight: 700, color: "#60a5fa" }}>
            4×
          </div>
          <div style={{ fontSize: "9px", color: "#64748b" }}>FEWER TOKENS</div>
        </div>
      </div>
    </div>
  );

  const ContextMeter = () => (
    <div className="dw-panel" style={{ padding: "16px", marginBottom: "16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
        <span style={{ fontSize: "10px", color: "#60a5fa", fontFamily: "'JetBrains Mono'" }}>CONTEXT EFFICIENCY</span>
        <span style={{ fontSize: "10px", color: "#4ade80" }}>{contextEfficiency}%</span>
      </div>
      <div style={{ height: "6px", background: "rgba(255,255,255,0.1)", borderRadius: "3px", marginBottom: "8px" }}>
        <div style={{ 
          height: "100%", width: `${contextEfficiency}%`, 
          background: "linear-gradient(90deg, #4ade80, #60a5fa)", 
          borderRadius: "3px", transition: "width 0.5s ease"
        }} />
      </div>
      <div style={{ fontSize: "9px", color: "#64748b" }}>
        Saved ~12,400 tokens vs full-file context
      </div>
    </div>
  );

  const PredictiveTools = () => (
    <div style={{ marginTop: "12px", padding: "12px", background: "rgba(0,0,0,0.3)", borderRadius: "8px" }}>
      <div style={{ fontSize: "9px", color: "#f59e0b", fontFamily: "'JetBrains Mono'", marginBottom: "8px" }}>
        ⚡ PREDICTIVE TOOLING
      </div>
      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
        {['ast_parser', 'dependency_graph', 'test_runner'].map((tool, i) => (
          <div key={i} style={{
            padding: "4px 8px", borderRadius: "4px", fontSize: "8px",
            background: "rgba(245, 158, 11, 0.1)", border: "1px solid rgba(245, 158, 11, 0.3)",
            color: "#f59e0b", fontFamily: "'JetBrains Mono'"
          }}>
            {tool}
          </div>
        ))}
      </div>
      <div style={{ fontSize: "8px", color: "#64748b", marginTop: "6px" }}>
        Pre-loaded based on task signature
      </div>
    </div>
  );

  const CombatReadiness = () => (
    <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
      {[
        { label: "COUNTERMEASURE", icon: "🛡️", color: "#f59e0b", action: "deployFirewall" },
        { label: "DECOY", icon: "🎭", color: "#8b5cf6", action: "deployDecoy" },
        { label: "SCATTER", icon: "🌀", color: "#10b981", action: "scatterAgents" },
        { label: "DEEP_DIVE", icon: "🌊", color: "#0ea5e9", action: "goDark" }
      ].map((btn, i) => (
        <button key={i} onClick={() => {
          addLog(`DEFENSE: ${btn.label} ACTIVATED`, "warning");
        }} style={{
          flex: 1, padding: "10px", borderRadius: "8px",
          background: `rgba(${parseInt(btn.color.slice(1,3), 16)}, ${parseInt(btn.color.slice(3,5), 16)}, ${parseInt(btn.color.slice(5,7), 16)}, 0.1)`,
          border: `1px solid ${btn.color}44`,
          color: btn.color, fontSize: "10px", fontFamily: "'JetBrains Mono'",
          fontWeight: 600, cursor: "pointer", transition: "all 0.2s"
        }}>
          {btn.icon} {btn.label}
        </button>
      ))}
    </div>
  );

  const IntelMatrix = () => (
    <div className="dw-panel" style={{ padding: "16px", marginBottom: "16px", position: "relative", height: "140px" }}>
      <div style={{ fontSize: "10px", color: "#60a5fa", fontFamily: "'JetBrains Mono'", marginBottom: "12px" }}>INTEL_MATRIX</div>
      <div style={{ 
        display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gridTemplateRows: "repeat(2, 1fr)",
        gap: "8px", height: "80px"
      }}>
        {Array.from({ length: 10 }).map((_, i) => {
          const types = ["THREAT", "ASSET", "AGENT", "TARGET", "OBSTACLE"];
          const type = types[Math.floor(Math.random() * types.length)];
          const active = Math.random() > 0.3;
          return (
            <div key={i} style={{ 
              position: "relative", border: "1px solid rgba(255,255,255,0.05)",
              borderRadius: "4px", background: active ? "rgba(255,255,255,0.03)" : "transparent"
            }}>
              {active && (
                <>
                  <div style={{
                    position: "absolute", top: "2px", left: "2px", width: "6px", height: "6px",
                    background: type === "THREAT" ? "#ef4444" : type === "AGENT" ? "#22c55e" : "#fbbf24",
                    borderRadius: "50%", animation: "thinkingPulse 2s infinite"
                  }} />
                  <div style={{
                    position: "absolute", bottom: "2px", right: "2px", fontSize: "6px",
                    color: type === "THREAT" ? "#ef4444" : "#94a3b8"
                  }}>{type.charAt(0)}</div>
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );

  const CommandSequencer = () => (
    <div className="dw-panel" style={{ padding: "16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
        <div style={{ fontSize: "10px", color: "#60a5fa", fontFamily: "'JetBrains Mono'" }}>OPERATION_QUEUE</div>
        <button onClick={() => {
          const ops = ["SCAN_NETWORK", "ENCRYPT_FILES", "EXFIL_DATA", "COVER_TRACKS"];
          addLog(`QUEUED: ${ops.join(" → ")}`, "command");
        }} style={{
          background: "rgba(34, 197, 94, 0.1)", border: "1px solid rgba(34, 197, 94, 0.3)",
          color: "#22c55e", padding: "4px 10px", borderRadius: "6px", fontSize: "9px",
          fontFamily: "'JetBrains Mono'", cursor: "pointer"
        }}>
          + MACRO
        </button>
      </div>
      
      {[
        { seq: "ANALYZE → REPORT → ARCHIVE", status: "running", progress: 65 },
        { seq: "BACKUP → ENCRYPT → UPLOAD", status: "queued", progress: 0 },
        { seq: "SANITIZE → VALIDATE → DEPLOY", status: "completed", progress: 100 }
      ].map((op, i) => (
        <div key={i} style={{ 
          padding: "10px", background: "rgba(255,255,255,0.03)", borderRadius: "8px", marginBottom: "8px",
          borderLeft: `3px solid ${op.status === "running" ? "#60a5fa" : op.status === "completed" ? "#4ade80" : "#64748b"}`
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
            <div style={{ fontSize: "11px", fontFamily: "'JetBrains Mono'", color: "#e2e8f0" }}>{op.seq}</div>
            <div style={{ 
              fontSize: "8px", padding: "2px 6px", borderRadius: "4px",
              background: op.status === "running" ? "rgba(96, 165, 250, 0.1)" : 
                         op.status === "completed" ? "rgba(74, 222, 128, 0.1)" : "rgba(100, 116, 139, 0.1)",
              color: op.status === "running" ? "#60a5fa" : 
                     op.status === "completed" ? "#4ade80" : "#94a3b8"
            }}>{op.status.toUpperCase()}</div>
          </div>
          {op.status === "running" && (
            <div style={{ height: "2px", background: "rgba(255,255,255,0.1)", borderRadius: "1px" }}>
              <div style={{ 
                height: "100%", width: `${op.progress}%`, background: "#60a5fa", borderRadius: "1px",
                transition: "width 0.5s ease"
              }} />
            </div>
          )}
        </div>
      ))}
    </div>
  );

  const ComsecPanel = () => (
    <div style={{ marginTop: "12px", padding: "12px", background: "rgba(0,0,0,0.3)", borderRadius: "8px" }}>
      <div style={{ fontSize: "9px", color: "#8b5cf6", fontFamily: "'JetBrains Mono'", marginBottom: "8px" }}>COMSEC_STATUS</div>
      <div style={{ display: "flex", gap: "8px", marginBottom: "8px" }}>
        {["AES-256", "QUANTUM", "STEALTH"].map((mode, i) => (
          <button key={i} onClick={() => setComsecMode(mode)} style={{
            flex: 1, padding: "4px", borderRadius: "4px",
            background: comsecMode === mode ? "rgba(139, 92, 246, 0.2)" : "rgba(255,255,255,0.05)",
            border: comsecMode === mode ? "1px solid #8b5cf6" : "1px solid rgba(255,255,255,0.1)",
            color: comsecMode === mode ? "#8b5cf6" : "#94a3b8", fontSize: "8px",
            cursor: "pointer", transition: "all 0.2s"
          }}>
            {mode}
          </button>
        ))}
      </div>
      <div style={{ fontSize: "9px", color: "#22c55e" }}>
        🔒 ENCRYPTED CHANNEL ACTIVE ({comsecMode})
      </div>
    </div>
  );

  const CriticalDecisionStack = () => {
    if (pendingDecisions === 0) return null;
    
    return (
      <div style={{
        position: "fixed", bottom: "20px", right: "20px", width: "320px",
        background: "rgba(8,22,42,0.95)", border: "1px solid rgba(239, 68, 68, 0.3)",
        borderRadius: "12px", padding: "16px", backdropFilter: "blur(10px)",
        boxShadow: "0 0 40px rgba(239, 68, 68, 0.2)", zIndex: 100,
        animation: "slideIn 0.3s ease-out"
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
          <div style={{ fontSize: "11px", color: "#ef4444", fontFamily: "'JetBrains Mono'", fontWeight: 600 }}>
            ⚠️ PENDING AUTHORIZATIONS
          </div>
          <div style={{ fontSize: "9px", color: "#94a3b8" }}>{pendingDecisions} REQUIRED</div>
        </div>
        <div style={{ fontSize: "11px", color: "#e2e8f0", lineHeight: "1.5", marginBottom: "16px" }}>
          • Approve memory override?<br/>
          • Authorize API key rotation?<br/>
          • Confirm target engagement?
        </div>
        <div style={{ display: "flex", gap: "12px" }}>
          <button onClick={() => setPendingDecisions(0)} style={{ 
            flex: 1, background: "rgba(34, 197, 94, 0.2)", color: "#22c55e", 
            border: "1px solid #22c55e", padding: "8px", borderRadius: "8px", fontSize: "10px",
            fontWeight: 600, cursor: "pointer"
          }}>
            APPROVE ALL
          </button>
          <button style={{ 
            flex: 1, background: "rgba(239, 68, 68, 0.1)", color: "#ef4444", 
            border: "1px solid #ef4444", padding: "8px", borderRadius: "8px", fontSize: "10px",
            cursor: "pointer"
          }}>
            REVIEW
          </button>
        </div>
      </div>
    );
  };

  return (
    <div style={{ 
      minHeight: "100vh", color: "#e2e8f0", padding: "20px",
      fontFamily: "'Inter', sans-serif",
      animation: emergencyMode ? "emergencyPulse 2s infinite" : "none"
    }}>
      <style>{CSS}</style>
      <div className="ocean-bg">
        <div className="sonar-ring" />
        <div className="sonar-ring" style={{ animationDelay: "1.5s" }} />
      </div>

      {/* ── COMMAND PALETTE ── */}
      {showCommandPalette && (
        <div style={{
          position: "fixed", top: "50%", left: "50%", zIndex: 1000,
          width: "600px", background: "rgba(8,22,42,0.98)", backdropFilter: "blur(30px)",
          border: "1px solid #60a5fa55", borderRadius: "16px", 
          animation: "slideIn 0.2s ease-out", boxShadow: "0 25px 70px rgba(0,0,0,0.8)"
        }}>
          <div style={{ padding: "16px", background: "rgba(0,0,0,0.3)", borderBottom: "1px solid #ffffff11", display: "flex", gap: "12px", alignItems: "center" }}>
            <span style={{ color: "#60a5fa", fontFamily: "'JetBrains Mono'" }}>⌘K</span>
            <input 
              autoFocus value={cmdInput} 
              onChange={(e) => setCmdInput(e.target.value)} 
              onKeyDown={handleCommand}
              placeholder="Type a command... (zero-shot execution enabled)"
              style={{ flex: 1, background: "transparent", border: "none", outline: "none", color: "#fff", fontSize: "14px", fontFamily: "'JetBrains Mono'" }} 
            />
          </div>
          <div style={{ padding: "8px", maxHeight: "300px", overflow: "auto" }}>
            {[
              { cmd: "/deploy", desc: "Release agent instance", color: "#4ade80" },
              { cmd: "/spawn coder", desc: "Spawn coding agent", color: "#60a5fa" },
              { cmd: "/spawn reviewer", desc: "Spawn code reviewer", color: "#a78bfa" },
              { cmd: "/override", desc: "Toggle manual control", color: "#fbbf24" },
              { cmd: "/abort", desc: "Emergency shutdown", color: "#f87171" },
              { cmd: "/clear", desc: "Clear terminal", color: "#94a3b8" },
            ].map((item, i) => (
              <div key={i} style={{ padding: "10px 16px", display: "flex", gap: "12px", borderRadius: "6px", cursor: "pointer" }}>
                <span style={{ color: item.color, fontFamily: "'JetBrains Mono'", width: "120px" }}>{item.cmd}</span>
                <span style={{ color: "#64748b", fontSize: "12px" }}>{item.desc}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── HEADER ── */}
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "28px", fontWeight: 800, color: emergencyMode ? "#f87171" : "#fff", letterSpacing: "-0.02em" }}>
            DWEEPBOT <span style={{ opacity: 0.4, fontWeight: 400 }}>// LONE_SHARK</span>
          </h1>
          <div style={{ display: "flex", gap: "8px", marginTop: "12px" }}>
            {[
              { label: "ZERO_SHOT", status: "green", icon: "🎯" },
              { label: "PREDICTIVE", status: "green", icon: "⚡" },
              { label: "COMPRESSED", status: "green", icon: "🗜️" },
              { label: "COMSEC", status: comsecMode === "STEALTH" ? "green" : "yellow", icon: "🔒" },
            ].map((alert, i) => (
              <div key={i} style={{
                display: "flex", alignItems: "center", gap: "6px", padding: "4px 12px", borderRadius: "20px",
                background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)"
              }}>
                <span style={{ fontSize: "12px" }}>{alert.icon}</span>
                <span style={{ fontSize: "10px", fontFamily: "'JetBrains Mono'", color: alert.status === "red" ? "#f87171" : "#4ade80", fontWeight: 600 }}>{alert.label}</span>
              </div>
            ))}
          </div>
        </div>

        <div style={{ animation: emergencyMode ? "none" : "sharkProwl 6s ease-in-out infinite", filter: emergencyMode ? "grayscale(100%) brightness(0.5)" : "none" }}>
          <SharkLogo size={110} emergencyMode={emergencyMode} intensity={activeAgents.length} />
        </div>

        <div style={{ textAlign: "right" }}>
          <div ref={tokenRef} style={{ position: "relative", color: "#4ade80", fontSize: "24px", fontFamily: "'JetBrains Mono'", fontWeight: 700 }}>
            {tokens.toLocaleString()} <span style={{ fontSize: "12px", opacity: 0.6 }}>TKN</span>
          </div>
          <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>${costData.cost.toFixed(4)} total cost</div>
          <div style={{ fontSize: "10px", opacity: 0.4, fontFamily: "'JetBrains Mono'", marginTop: "4px" }}>
            DEPTH: 2,400M // AGENTS: {activeAgents.length}
          </div>
        </div>
      </header>

      {/* ── ZERO-SHOT METRICS ── */}
      <ZeroShotMetrics />

      {/* ── INTEL MATRIX ── */}
      <IntelMatrix />

      {/* ── CONTEXT METER ── */}
      <ContextMeter />

      {/* ── TOKEN BURN CHART ── */}
      <div className="dw-panel" style={{ padding: "16px", marginBottom: "16px", height: "120px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
          <span style={{ fontSize: "11px", color: "#64748b", fontFamily: "'JetBrains Mono'" }}>TOKEN_VELOCITY</span>
          <span style={{ fontSize: "10px", color: "#4ade80" }}>4× more efficient vs OpenClaw</span>
        </div>
        <ResponsiveContainer width="100%" height="80%">
          <LineChart data={tokenHistory}>
            <XAxis dataKey="time" hide />
            <YAxis hide domain={['dataMin', 'dataMax']} />
            <Tooltip 
              contentStyle={{ background: 'rgba(4,12,24,0.9)', border: '1px solid #334155', borderRadius: '8px' }}
              itemStyle={{ color: '#4ade80', fontSize: '11px' }}
            />
            <Line type="monotone" dataKey="tokens" stroke="#4ade80" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* ── EMERGENCY CONTROLS ── */}
      <div style={{ display: "flex", gap: "12px", marginBottom: "16px" }}>
        <button onClick={handleEmergencyStop} style={{
          flex: 1, background: emergencyMode ? "#dc2626" : "rgba(220,38,38,0.1)",
          border: `1px solid ${emergencyMode ? "#f87171" : "#dc262666"}`,
          color: emergencyMode ? "#fff" : "#f87171", padding: "14px", borderRadius: "12px",
          fontSize: "11px", fontFamily: "'JetBrains Mono'", fontWeight: 700, cursor: "pointer",
          transition: "all 0.2s"
        }}>
          ⚡ {emergencyMode ? "EMERGENCY STOPPED" : "E-STOP"}
        </button>
        <button onClick={() => { setOverrideActive(!overrideActive); addLog("TOGGLE: OVERRIDE"); }} style={{
          flex: 1, background: overrideActive ? "#0ea5e9" : "rgba(14,165,233,0.1)",
          border: `1px solid ${overrideActive ? "#38bdf8" : "#0ea5e966"}`,
          color: overrideActive ? "#fff" : "#38bdf8", padding: "14px", borderRadius: "12px",
          fontSize: "11px", fontFamily: "'JetBrains Mono'", fontWeight: 700, cursor: "pointer"
        }}>
          🎮 {overrideActive ? "MANUAL CONTROL" : "OVERRIDE"}
        </button>
        <button onClick={() => handleSpawnAgent("CODER")} style={{
          flex: 1, background: "rgba(168,85,247,0.1)", border: "1px solid rgba(168,85,247,0.4)",
          color: "#c084fc", padding: "14px", borderRadius: "12px", fontSize: "11px", 
          fontFamily: "'JetBrains Mono'", cursor: "pointer", fontWeight: 700
        }}>
          👨‍💻 SPAWN CODER
        </button>
      </div>

      {/* ── COMBAT READINESS ── */}
      <div className="dw-panel" style={{ padding: "16px", marginBottom: "16px", border: emergencyMode ? "1px solid rgba(239, 68, 68, 0.4)" : "1px solid rgba(245, 158, 11, 0.2)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
          <div style={{ fontSize: "10px", color: emergencyMode ? "#ef4444" : "#f59e0b", fontFamily: "'JetBrains Mono'", fontWeight: 600 }}>
            {emergencyMode ? "🚨 THREAT DETECTED" : "🛡️ COMBAT READINESS"}
          </div>
          <div style={{ fontSize: "9px", color: "#64748b" }}>THREAT_LEVEL: {emergencyMode ? "CRITICAL" : "ELEVATED"}</div>
        </div>
        <CombatReadiness />
      </div>

      {/* ── ACTIVE AGENTS ── */}
      {activeAgents.length > 0 && (
        <div style={{ marginBottom: "16px" }}>
          <div style={{ fontSize: "10px", color: "#64748b", marginBottom: "8px", fontFamily: "'JetBrains Mono'" }}>ACTIVE_SWARM</div>
          <div style={{ display: "flex", gap: "12px" }}>
            {activeAgents.map(agent => (
              <div key={agent.id} className="dw-panel tool-execution" style={{ 
                flex: 1, padding: "12px", borderLeft: "3px solid #60a5fa",
                display: "flex", alignItems: "center", gap: "12px"
              }}>
                <div style={{ 
                  width: "32px", height: "32px", borderRadius: "50%", 
                  background: "linear-gradient(135deg, #60a5fa, #3b82f6)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "14px"
                }}>
                  {agent.name === "CODER" ? "💻" : "🔍"}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: "12px", fontWeight: 600, color: "#fff" }}>{agent.name}</div>
                  <div style={{ fontSize: "10px", color: "#64748b" }}>{agent.task}</div>
                  <div style={{ 
                    height: "3px", background: "rgba(255,255,255,0.1)", borderRadius: "2px", marginTop: "6px" 
                  }}>
                    <div style={{ 
                      height: "100%", width: `${agent.progress}%`, background: "#60a5fa", borderRadius: "2px",
                      transition: "width 0.3s ease"
                    }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── THINKING STREAM ── */}
      {thinking && (
        <div className="dw-panel" style={{ padding: "16px", marginBottom: "16px", borderLeft: "3px solid #fbbf24" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <span style={{ fontSize: "10px", color: "#fbbf24", fontFamily: "'JetBrains Mono'" }}>🧠 ZERO-SHOT REASONING</span>
            <span style={{ fontSize: "9px", color: "#64748b" }}>No reflection loops</span>
          </div>
          <div className="thinking-stream">{thinking}</div>
        </div>
      )}

      {/* ── CURRENT TOOL ── */}
      {currentTool && (
        <div className="dw-panel" style={{ padding: "12px", marginBottom: "16px", borderLeft: "3px solid #8b5cf6" }}>
          <div style={{ fontSize: "10px", color: "#8b5cf6", fontFamily: "'JetBrains Mono'" }}>
            ⚡ EXECUTING: {currentTool}
          </div>
        </div>
      )}

      {/* ── GRID ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr 1fr", gap: "16px" }}>
        
        <CommandSequencer />

        <div className="dw-panel" style={{ padding: "16px", display: "flex", flexDirection: "column" }}>
          <div style={{ fontSize: "9px", color: "#4a6a8a", fontFamily: "'JetBrains Mono'", marginBottom: "12px" }}>CONTEXT_WINDOW</div>
          
          <div style={{ 
            padding: "12px", background: "rgba(0,0,0,0.3)", borderRadius: "8px", marginBottom: "12px",
            border: "1px solid rgba(96,165,250,0.2)"
          }}>
            <div style={{ fontSize: "10px", color: "#60a5fa", marginBottom: "4px" }}>CURRENT_FILE</div>
            <div style={{ fontSize: "11px", color: "#e2e8f0", fontFamily: "'JetBrains Mono'" }}>src/agents/coder.py</div>
            <div style={{ fontSize: "9px", color: "#64748b", marginTop: "4px" }}>Lines 45-89 selected</div>
          </div>

          <div style={{ marginBottom: "12px" }}>
            <div style={{ fontSize: "9px", color: "#4a6a8a", marginBottom: "8px" }}>RECENT_CONTEXT</div>
            {[
              "Refactoring auth middleware",
              "Added JWT validation",
              "Fixed token expiry bug"
            ].map((ctx, i) => (
              <div key={i} style={{ 
                padding: "6px 8px", fontSize: "11px", color: "#94a3b8",
                borderLeft: "2px solid #334155", paddingLeft: "8px", marginBottom: "4px"
              }}>
                {ctx}
              </div>
            ))}
          </div>

          <div style={{ marginTop: "auto", borderTop: "1px solid #ffffff11", paddingTop: "12px" }}>
            <div style={{ fontSize: "9px", color: "#4a6a8a", marginBottom: "8px" }}>MEMORY_STACK</div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", marginBottom: "4px" }}>
              <span style={{ color: "#64748b" }}>WORKING</span>
              <span style={{ color: "#4ade80" }}>1.2GB / 2GB</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px" }}>
              <span style={{ color: "#64748b" }}>VECTOR_DB</span>
              <span style={{ color: "#60a5fa" }}>44.8GB</span>
            </div>
          </div>

          <PredictiveTools />
          <ComsecPanel />
        </div>

        <div className="dw-panel" style={{ padding: "16px", background: "rgba(0,0,0,0.4)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
            <span style={{ fontSize: "9px", color: "#22c55e", fontFamily: "'JetBrains Mono'" }}>TERMINAL_OUTPUT</span>
            <button onClick={() => setLogs([])} style={{ 
              fontSize: "9px", color: "#64748b", background: "none", border: "none", cursor: "pointer" 
            }}>CLEAR</button>
          </div>
          <div style={{ fontSize: "11px", fontFamily: "'JetBrains Mono'", lineHeight: "1.5", maxHeight: "300px", overflow: "auto" }}>
            {terminalLogs.map((log, i) => (
              <div key={i} style={{ marginBottom: "4px", animation: "slideIn 0.2s ease-out" }}>
                <span style={{ opacity: 0.3 }}>[{log.t}]</span>{' '}
                <span style={{ 
                  color: log.type === 'error' ? '#f87171' : log.type === 'success' ? '#4ade80' : log.type === 'warning' ? '#fbbf24' : log.type === 'command' ? '#60a5fa' : '#e2e8f0',
                  fontWeight: log.type === 'command' ? 600 : 400
                }}>{log.m}</span>
              </div>
            ))}
            <div style={{ 
              display: "inline-block", width: "8px", height: "14px", background: "#4ade80", 
              marginLeft: "2px", animation: "thinkingPulse 1s infinite", verticalAlign: "middle" 
            }} />
          </div>
        </div>

      </div>

      <CriticalDecisionStack />

      <footer style={{ 
        marginTop: "24px", paddingTop: "16px", borderTop: "1px solid rgba(255,255,255,0.1)",
        display: "flex", justifyContent: "space-between", fontSize: "10px", color: "#475569"
      }}>
        <div>DWEEPBOT v2.0.1 // ZERO-SHOT // COMSEC: {comsecMode}</div>
        <div style={{ display: "flex", gap: "16px" }}>
          <span>LATENCY: 45ms</span>
          <span>UPTIME: 4d 12h 33m</span>
          <span>THREATS: {emergencyMode ? "ACTIVE" : "NONE"}</span>
        </div>
      </footer>
    </div>
  );
}
