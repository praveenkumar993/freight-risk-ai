import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { MapContainer, TileLayer, Polyline, Tooltip } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const API = "http://localhost:8000";

const HIGHWAY_COORDS = {
  "NH-44":  [[28.61,77.21],[21.15,79.09],[17.39,78.49],[12.97,77.59],[12.52,78.21],[13.08,80.27]],
  "NH-48":  [[19.08,72.88],[18.52,73.86],[15.36,75.12],[12.97,77.59]],
  "NH-16":  [[13.08,80.27],[14.44,79.99],[16.31,80.44],[16.51,80.65],[17.00,81.80],[16.99,82.25],[17.69,83.22]],
  "NH-275": [[12.97,77.59],[12.30,76.64],[11.02,76.96],[10.53,76.21],[9.93,76.27],[11.26,75.78],[8.52,76.94]],
  "NH-65":  [[17.39,78.49],[17.98,79.59],[18.67,78.09],[15.83,78.04],[17.66,75.91],[18.52,73.86]],
  "NH-544": [[13.08,80.27],[12.92,79.13],[11.66,78.15],[10.79,78.70],[9.93,78.12],[11.02,76.96]],
  "NH-30":  [[13.08,80.27],[13.63,79.42],[14.47,78.82],[15.83,78.04]],
  "NH-340": [[15.85,74.50],[15.36,75.12],[14.46,75.92],[12.91,74.86]],
};

const CITIES = [
  "Delhi","Nagpur","Hyderabad","Bangalore","Chennai","Krishnagiri",
  "Mumbai","Pune","Hubli","Vijayawada","Visakhapatnam","Nellore",
  "Guntur","Rajahmundry","Kakinada","Mysore","Coimbatore","Kochi",
  "Thrissur","Kozhikode","Thiruvananthapuram","Kurnool","Solapur",
  "Warangal","Nizamabad","Salem","Vellore","Madurai","Tiruchirappalli",
  "Tirupati","Kadapa","Mangalore","Davangere","Belgaum"
];

const PRODUCTS = [
  "Electronics","Pharmaceuticals","Food & Perishables",
  "Automotive Parts","Textiles","Industrial Machinery",
  "FMCG","Chemicals","Construction Materials"
];

const RC = { HIGH:"#ff3b3b", MEDIUM:"#ffb800", LOW:"#00e676" };
const RL = hw => RC[hw] || RC.LOW;

const GUARDRAIL_KEYWORDS = [
  "highway","route","risk","freight","truck","transport","road","nh-",
  "nh44","nh48","nh16","nh65","nh275","nh544","nh30","nh340",
  "disruption","flood","rain","monsoon","strike","accident","landslide",
  "cyclone","congestion","delay","shipment","logistics","cargo","delivery",
  "bangalore","hyderabad","chennai","mumbai","delhi","pune","kochi",
  "vijayawada","visakhapatnam","coimbatore","mysore","safe","dangerous",
  "score","weather","traffic","condition","corridor","south india"
];

function isFreightQuestion(msg) {
  const lower = msg.toLowerCase();
  return GUARDRAIL_KEYWORDS.some(k => lower.includes(k));
}

export default function App() {
  const [highways, setHighways] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    origin:"Hyderabad", destination:"Chennai",
    product_type:"Electronics", quantity_kg:500,
    transport_mode:"Road", expected_date:"2026-05-20"
  });
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatMsgs, setChatMsgs] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [sparkle, setSparkle] = useState(false);
  const [activeSection, setActiveSection] = useState("overview");
  const chatEndRef = useRef(null);

  useEffect(() => { fetchHighways(); }, []);
  useEffect(() => {
    const t = setInterval(() => setSparkle(s => !s), 2000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior:"smooth" });
  }, [chatMsgs]);

  const fetchHighways = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API}/highway-risk`);
      setHighways(res.data);
    } catch(e) { console.error(e); }
    finally { setLoading(false); }
  };

  const handleAnalyze = async () => {
    try {
      setAnalyzing(true);
      setAnalysis(null);
      const res = await axios.post(`${API}/analyze`, form);
      setAnalysis(res.data);
      setActiveSection("result");
    } catch(e) { console.error(e); }
    finally { setAnalyzing(false); }
  };

  const handleChat = async () => {
    if (!chatInput.trim()) return;
    const msg = chatInput.trim();
    setChatInput("");

    if (!isFreightQuestion(msg)) {
      setChatMsgs(p => [...p,
        { role:"user", text:msg },
        { role:"bot", text:"I can only answer questions about Indian highway freight risk, routes, disruptions, and logistics conditions. Try asking about NH-44, route safety, or current highway conditions." }
      ]);
      return;
    }

    setChatMsgs(p => [...p, { role:"user", text:msg }]);
    setChatLoading(true);
    try {
      const res = await axios.post(`${API}/chat`, { message:msg });
      setChatMsgs(p => [...p, { role:"bot", text:res.data.response }]);
    } catch(e) {
      setChatMsgs(p => [...p, { role:"bot", text:"Connection error. Make sure the backend is running." }]);
    } finally { setChatLoading(false); }
  };

  const highRisk = highways.filter(h => h.risk_level === "HIGH").length;
  const medRisk  = highways.filter(h => h.risk_level === "MEDIUM").length;
  const lowRisk  = highways.filter(h => h.risk_level === "LOW").length;

  return (
    <div style={{ fontFamily:"'DM Mono', monospace", background:"#080b12", minHeight:"100vh", color:"#c9d1e0" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Syne:wght@700;800&display=swap');
        * { box-sizing:border-box; margin:0; padding:0; }
        ::-webkit-scrollbar { width:4px; }
        ::-webkit-scrollbar-track { background:#0d1117; }
        ::-webkit-scrollbar-thumb { background:#1e3a5f; border-radius:2px; }
        select, input { font-family:'DM Mono', monospace !important; }
        option { background:#0d1117; }
        @keyframes pulse-ring {
          0% { transform:scale(1); opacity:0.8; }
          50% { transform:scale(1.15); opacity:0.4; }
          100% { transform:scale(1); opacity:0.8; }
        }
        @keyframes sparkle-float {
          0%,100% { transform:translateY(0) scale(1); }
          50% { transform:translateY(-6px) scale(1.05); }
        }
        @keyframes slide-up {
          from { transform:translateY(20px); opacity:0; }
          to { transform:translateY(0); opacity:1; }
        }
        @keyframes blink {
          0%,100% { opacity:1; } 50% { opacity:0; }
        }
        @keyframes spin {
          from { transform:rotate(0deg); }
          to { transform:rotate(360deg); }
        }
        @keyframes dot-bounce {
          0%,100% { transform:translateY(0); }
          50% { transform:translateY(-5px); }
        }
        .hw-row:hover { background:#0f1823 !important; }
        .nav-btn:hover { background:#0f1823 !important; color:#4fc3f7 !important; }
        .analyze-btn:hover { filter:brightness(1.1); transform:translateY(-1px); }
        .chat-fab:hover { transform:scale(1.08); }
      `}</style>

      {/* Top Bar */}
      <div style={{
        display:"flex", alignItems:"center", justifyContent:"space-between",
        padding:"0 28px", height:52, background:"#0d1117",
        borderBottom:"1px solid #1a2332", position:"sticky", top:0, zIndex:100
      }}>
        <div style={{ display:"flex", alignItems:"center", gap:12 }}>
          <div style={{
            width:28, height:28, borderRadius:6,
            background:"linear-gradient(135deg,#0077ff,#00c6ff)",
            display:"flex", alignItems:"center", justifyContent:"center",
            fontSize:14
          }}>⬡</div>
          <span style={{
            fontFamily:"'Syne',sans-serif", fontSize:15,
            fontWeight:800, color:"#e8f0fe", letterSpacing:1
          }}>FREIGHT RISK AI</span>
          <span style={{
            fontSize:9, color:"#0077ff", background:"#001a3d",
            padding:"2px 8px", borderRadius:3, letterSpacing:2,
            border:"1px solid #003080"
          }}>INDIA OPS</span>
        </div>

        <div style={{ display:"flex", alignItems:"center", gap:24 }}>
          <div style={{ display:"flex", gap:4 }}>
            {["overview","analyze","result"].map(s => (
              <button key={s} className="nav-btn" onClick={() => setActiveSection(s)} style={{
                background: activeSection===s ? "#0f1823" : "transparent",
                border:"none", color: activeSection===s ? "#4fc3f7" : "#4a5568",
                padding:"6px 14px", borderRadius:4, cursor:"pointer",
                fontSize:10, letterSpacing:1.5, textTransform:"uppercase",
                fontFamily:"'DM Mono',monospace",
                borderBottom: activeSection===s ? "2px solid #0077ff" : "2px solid transparent"
              }}>{s}</button>
            ))}
          </div>

          <div style={{ display:"flex", alignItems:"center", gap:6 }}>
            <div style={{
              width:6, height:6, borderRadius:"50%",
              background:"#00e676", animation:"pulse-ring 2s infinite"
            }}/>
            <span style={{ fontSize:9, color:"#4a5568", letterSpacing:1 }}>LIVE</span>
          </div>

          <button onClick={fetchHighways} style={{
            background:"transparent", border:"1px solid #1a2332",
            color:"#4a5568", padding:"4px 10px", borderRadius:4,
            cursor:"pointer", fontSize:10, fontFamily:"'DM Mono',monospace",
            letterSpacing:1
          }}>⟳ SYNC</button>
        </div>
      </div>

      {/* Stats Bar */}
      <div style={{
        display:"flex", gap:1, background:"#0a0e17",
        borderBottom:"1px solid #1a2332"
      }}>
        {[
          { label:"TOTAL HIGHWAYS", val:highways.length, color:"#4fc3f7" },
          { label:"HIGH RISK", val:highRisk, color:"#ff3b3b" },
          { label:"MEDIUM RISK", val:medRisk, color:"#ffb800" },
          { label:"LOW RISK", val:lowRisk, color:"#00e676" },
          { label:"SEGMENTS TRACKED", val:36, color:"#4fc3f7" },
          { label:"CITIES COVERED", val:35, color:"#4fc3f7" },
          { label:"MODEL", val:"XGBoost v2", color:"#bb86fc" },
          { label:"PIPELINE", val:"Airflow+Kafka+Spark", color:"#bb86fc" },
        ].map((s,i) => (
          <div key={i} style={{
            flex:1, padding:"8px 14px",
            borderRight:"1px solid #1a2332"
          }}>
            <div style={{ fontSize:8, color:"#4a5568", letterSpacing:1.5, marginBottom:3 }}>
              {s.label}
            </div>
            <div style={{ fontSize:14, fontWeight:500, color:s.color }}>
              {s.val}
            </div>
          </div>
        ))}
      </div>

      {/* Main Layout */}
      <div style={{ display:"flex", height:"calc(100vh - 105px)" }}>

        {/* Sidebar */}
        <div style={{
          width:320, background:"#0d1117",
          borderRight:"1px solid #1a2332",
          display:"flex", flexDirection:"column",
          overflow:"hidden"
        }}>

          {/* Overview */}
          {activeSection === "overview" && (
            <div style={{ flex:1, overflow:"auto", padding:"16px 12px" }}>
              <div style={{
                fontSize:9, color:"#4a5568", letterSpacing:2,
                marginBottom:12, paddingLeft:4
              }}>CORRIDOR STATUS</div>
              {loading ? (
                <div style={{ textAlign:"center", padding:40, color:"#4a5568", fontSize:11 }}>
                  FETCHING DATA...
                </div>
              ) : highways.map((hw,i) => (
                <div key={hw.highway} className="hw-row" style={{
                  padding:"10px 12px", marginBottom:4,
                  background:"#090d14", borderRadius:4,
                  borderLeft:`3px solid ${RL(hw.risk_level)}`,
                  cursor:"default", transition:"background 0.2s",
                  animation:`slide-up 0.3s ease ${i*0.05}s both`
                }}>
                  <div style={{
                    display:"flex", justifyContent:"space-between",
                    alignItems:"center", marginBottom:6
                  }}>
                    <span style={{
                      fontFamily:"'Syne',sans-serif",
                      fontSize:13, fontWeight:700, color:"#e8f0fe"
                    }}>{hw.highway}</span>
                    <span style={{
                      fontSize:9, letterSpacing:1.5,
                      color:RL(hw.risk_level),
                      background:`${RL(hw.risk_level)}15`,
                      padding:"2px 8px", borderRadius:2,
                      border:`1px solid ${RL(hw.risk_level)}40`
                    }}>{hw.risk_level}</span>
                  </div>
                  <div style={{ position:"relative", height:3, background:"#1a2332", borderRadius:2, marginBottom:6 }}>
                    <div style={{
                      position:"absolute", left:0, top:0, height:"100%",
                      width:`${Math.max(hw.risk_score||0, 2)}%`,
                      background:`linear-gradient(90deg, ${RL(hw.risk_level)}88, ${RL(hw.risk_level)})`,
                      borderRadius:2, transition:"width 1s ease"
                    }}/>
                  </div>
                  <div style={{
                    display:"flex", justifyContent:"space-between",
                    fontSize:10, color:"#4a5568"
                  }}>
                    <span>SCORE <span style={{ color:RL(hw.risk_level) }}>{(hw.risk_score||0).toFixed(1)}</span></span>
                    <span style={{ color:"#2d3f52", fontSize:9 }}>{hw.weather_summary}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Analyze Form */}
          {activeSection === "analyze" && (
            <div style={{ flex:1, overflow:"auto", padding:"16px 12px" }}>
              <div style={{
                fontSize:9, color:"#4a5568", letterSpacing:2,
                marginBottom:14, paddingLeft:4
              }}>SHIPMENT PARAMETERS</div>

              {[
                { label:"ORIGIN", key:"origin", type:"select", opts:CITIES },
                { label:"DESTINATION", key:"destination", type:"select", opts:CITIES },
                { label:"PRODUCT TYPE", key:"product_type", type:"select", opts:PRODUCTS },
                { label:"QUANTITY (KG)", key:"quantity_kg", type:"number" },
                { label:"TRANSPORT MODE", key:"transport_mode", type:"select", opts:["Road","Rail"] },
                { label:"EXPECTED DATE", key:"expected_date", type:"date" },
              ].map(f => (
                <div key={f.key} style={{ marginBottom:12 }}>
                  <label style={{
                    fontSize:9, color:"#4a5568", letterSpacing:1.5,
                    display:"block", marginBottom:5
                  }}>{f.label}</label>
                  {f.type === "select" ? (
                    <select
                      value={form[f.key]}
                      onChange={e => setForm(p => ({...p,[f.key]:e.target.value}))}
                      style={{
                        width:"100%", background:"#090d14",
                        border:"1px solid #1a2332", borderRadius:4,
                        padding:"8px 10px", color:"#c9d1e0",
                        fontSize:11, outline:"none"
                      }}
                    >
                      {f.opts.map(o => <option key={o}>{o}</option>)}
                    </select>
                  ) : (
                    <input
                      type={f.type} value={form[f.key]}
                      onChange={e => setForm(p => ({
                        ...p, [f.key]: f.type==="number"
                          ? parseFloat(e.target.value)||0
                          : e.target.value
                      }))}
                      style={{
                        width:"100%", background:"#090d14",
                        border:"1px solid #1a2332", borderRadius:4,
                        padding:"8px 10px", color:"#c9d1e0",
                        fontSize:11, outline:"none"
                      }}
                    />
                  )}
                </div>
              ))}

              <button
                className="analyze-btn"
                onClick={handleAnalyze}
                disabled={analyzing}
                style={{
                  width:"100%", padding:"11px",
                  background: analyzing
                    ? "#1a2332"
                    : "linear-gradient(135deg,#0055cc,#0077ff)",
                  border:"none", borderRadius:4,
                  color:"white", fontSize:11, letterSpacing:2,
                  fontFamily:"'DM Mono',monospace",
                  cursor: analyzing ? "not-allowed" : "pointer",
                  transition:"all 0.2s", marginTop:4,
                  display:"flex", alignItems:"center", justifyContent:"center", gap:8
                }}
              >
                {analyzing ? (
                  <>
                    <div style={{
                      width:12, height:12, border:"2px solid #fff3",
                      borderTop:"2px solid white", borderRadius:"50%",
                      animation:"spin 0.8s linear infinite"
                    }}/>
                    ANALYZING ROUTE...
                  </>
                ) : "▶ RUN RISK ANALYSIS"}
              </button>
            </div>
          )}

          {/* Results */}
          {activeSection === "result" && (
            <div style={{ flex:1, overflow:"auto", padding:"16px 12px" }}>
              {!analysis ? (
                <div style={{
                  textAlign:"center", padding:"60px 20px",
                  color:"#4a5568", fontSize:11, letterSpacing:1
                }}>
                  <div style={{ fontSize:32, marginBottom:12 }}>◈</div>
                  RUN AN ANALYSIS FIRST
                </div>
              ) : (
                <div style={{ animation:"slide-up 0.4s ease" }}>
                  {/* Risk Score Card */}
                  <div style={{
                    background:"#090d14",
                    border:`1px solid ${RL(analysis.risk_level)}40`,
                    borderRadius:4, padding:14, marginBottom:10,
                    position:"relative", overflow:"hidden"
                  }}>
                    <div style={{
                      position:"absolute", top:0, right:0,
                      width:80, height:80, borderRadius:"0 0 0 80px",
                      background:`${RL(analysis.risk_level)}08`
                    }}/>
                    <div style={{ fontSize:9, color:"#4a5568", letterSpacing:2, marginBottom:8 }}>
                      RISK ASSESSMENT
                    </div>
                    <div style={{
                      display:"flex", alignItems:"baseline",
                      gap:6, marginBottom:6
                    }}>
                      <span style={{
                        fontFamily:"'Syne',sans-serif",
                        fontSize:36, fontWeight:800,
                        color:RL(analysis.risk_level), lineHeight:1
                      }}>
                        {(analysis.risk_score||0).toFixed(1)}
                      </span>
                      <span style={{ fontSize:9, color:"#4a5568" }}>/100</span>
                      <span style={{
                        marginLeft:"auto", fontSize:11,
                        color:RL(analysis.risk_level),
                        background:`${RL(analysis.risk_level)}15`,
                        padding:"3px 10px", borderRadius:2,
                        border:`1px solid ${RL(analysis.risk_level)}40`,
                        letterSpacing:1
                      }}>{analysis.risk_level}</span>
                    </div>
                    <div style={{
                      display:"flex", gap:16, fontSize:10,
                      color:"#4a5568", marginBottom:8
                    }}>
                      <span>DELAY PROB <span style={{ color:"#c9d1e0" }}>{(analysis.delay_probability||0).toFixed(1)}%</span></span>
                      <span>ETA IMPACT <span style={{ color:"#c9d1e0" }}>+{analysis.expected_delay_days}d</span></span>
                    </div>
                    <div style={{
                      fontSize:10, color:"#4a5568",
                      lineHeight:1.6, borderTop:"1px solid #1a2332",
                      paddingTop:8
                    }}>
                      {analysis.root_cause}
                    </div>
                  </div>

                  {/* Routes */}
                  {[
                    { data:analysis.primary_route, label:"PRIMARY ROUTE", color:"#0077ff" },
                    { data:analysis.alternate_route, label:"ALTERNATE ROUTE", color:"#ffb800" }
                  ].map(({data, label, color}) => data && (
                    <div key={label} style={{
                      background:"#090d14", borderRadius:4,
                      padding:12, marginBottom:8,
                      borderLeft:`2px solid ${color}`
                    }}>
                      <div style={{
                        fontSize:9, color:color,
                        letterSpacing:2, marginBottom:8
                      }}>{label}</div>
                      <div style={{
                        display:"flex", gap:16,
                        fontSize:10, color:"#4a5568", marginBottom:8
                      }}>
                        <span>⏱ {data.duration_hours}hrs</span>
                        <span>📍 {data.distance_km}km</span>
                        <span style={{ color:RL(data.risk_level) }}>
                          ● {data.risk_level}
                        </span>
                      </div>
                      <div style={{
                        display:"flex", flexWrap:"wrap",
                        gap:3, fontSize:9, color:"#4a5568"
                      }}>
                        {data.path?.map((city,i) => (
                          <span key={i}>
                            <span style={{ color:"#2d4a6e" }}>{city}</span>
                            {i < data.path.length-1 && (
                              <span style={{ color:"#1a2332" }}> → </span>
                            )}
                          </span>
                        ))}
                      </div>
                      <div style={{
                        marginTop:6, fontSize:9,
                        color:color, opacity:0.7
                      }}>
                        {data.highways?.join(" + ")}
                      </div>
                    </div>
                  ))}

                  {/* Mitigation */}
                  <div style={{
                    fontSize:9, color:"#4a5568",
                    letterSpacing:2, marginBottom:8, marginTop:12
                  }}>MITIGATION OPTIONS</div>
                  {analysis.mitigation?.map((m,i) => (
                    <div key={i} style={{
                      display:"flex", justifyContent:"space-between",
                      alignItems:"flex-start",
                      padding:"8px 10px", marginBottom:4,
                      background:"#090d14", borderRadius:3,
                      borderLeft:`2px solid ${i===0?"#0077ff":i===1?"#ffb800":"#2d3f52"}`
                    }}>
                      <div>
                        <div style={{ fontSize:10, color:"#c9d1e0", marginBottom:2 }}>
                          {m.option}
                        </div>
                        <div style={{ fontSize:9, color:"#4a5568" }}>{m.detail}</div>
                      </div>
                      <div style={{ textAlign:"right" }}>
                        <div style={{ fontSize:9, color:"#4a5568" }}>{m.time_impact}</div>
                        <div style={{ fontSize:9, color:"#0077ff" }}>{m.cost_impact}</div>
                      </div>
                    </div>
                  ))}

                  {/* SHAP */}
                  <div style={{
                    fontSize:9, color:"#4a5568",
                    letterSpacing:2, marginBottom:8, marginTop:12
                  }}>SHAP RISK FACTORS</div>
                  {analysis.shap_explanation?.map((s,i) => (
                    <div key={i} style={{
                      display:"flex", justifyContent:"space-between",
                      alignItems:"center", padding:"5px 0",
                      borderBottom:"1px solid #0f1520"
                    }}>
                      <span style={{ fontSize:9, color:"#4a5568" }}>{s.feature}</span>
                      <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                        <div style={{
                          width:40, height:2, background:"#1a2332",
                          borderRadius:1, overflow:"hidden"
                        }}>
                          <div style={{
                            width:`${Math.min(Math.abs(s.impact)*15,100)}%`,
                            height:"100%",
                            background: s.impact>0 ? "#ff3b3b" : "#00e676"
                          }}/>
                        </div>
                        <span style={{
                          fontSize:9, fontFamily:"'DM Mono',monospace",
                          color: s.impact>0 ? "#ff3b3b" : "#00e676",
                          minWidth:50, textAlign:"right"
                        }}>
                          {s.impact>0?"+":""}{s.impact?.toFixed(3)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Map Area */}
        <div style={{ flex:1, position:"relative" }}>
          <MapContainer
            center={[17,78]} zoom={6}
            style={{ height:"100%", width:"100%" }}
            zoomControl={false}
          >
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              attribution=""
            />
            {highways.map(hw => (
              HIGHWAY_COORDS[hw.highway] && (
                <Polyline
                  key={hw.highway}
                  positions={HIGHWAY_COORDS[hw.highway]}
                  color={RL(hw.risk_level)}
                  weight={hw.risk_level==="HIGH" ? 5 : 3}
                  opacity={hw.risk_level==="HIGH" ? 1 : 0.7}
                >
                  <Tooltip sticky>
                    <div style={{ fontFamily:"'DM Mono',monospace", fontSize:11 }}>
                      <strong>{hw.highway}</strong><br/>
                      Risk: {hw.risk_level} ({(hw.risk_score||0).toFixed(1)})<br/>
                      {hw.weather_summary}
                    </div>
                  </Tooltip>
                </Polyline>
              )
            ))}
          </MapContainer>

          {/* Map Overlays */}
          <div style={{
            position:"absolute", top:12, left:12, zIndex:999,
            background:"rgba(8,11,18,0.85)",
            border:"1px solid #1a2332", borderRadius:4,
            padding:"10px 14px", backdropFilter:"blur(8px)"
          }}>
            <div style={{
              fontSize:9, color:"#4a5568",
              letterSpacing:2, marginBottom:8
            }}>RISK LEGEND</div>
            {[["HIGH","#ff3b3b"],["MEDIUM","#ffb800"],["LOW","#00e676"]].map(([l,c]) => (
              <div key={l} style={{
                display:"flex", alignItems:"center",
                gap:8, marginBottom:4
              }}>
                <div style={{
                  width:20, height:3,
                  background:c, borderRadius:2
                }}/>
                <span style={{ fontSize:9, color:"#4a5568", letterSpacing:1 }}>{l}</span>
              </div>
            ))}
          </div>

          <div style={{
            position:"absolute", top:12, right:12, zIndex:999,
            background:"rgba(8,11,18,0.85)",
            border:"1px solid #1a2332", borderRadius:4,
            padding:"10px 14px", backdropFilter:"blur(8px)"
          }}>
            <div style={{
              fontSize:9, color:"#4a5568",
              letterSpacing:2, marginBottom:8
            }}>PIPELINE STATUS</div>
            {[
              ["KAFKA","STREAMING"],
              ["SPARK","PROCESSING"],
              ["AIRFLOW","SCHEDULED"],
              ["XGBOOST","ACTIVE"],
            ].map(([sys,status]) => (
              <div key={sys} style={{
                display:"flex", justifyContent:"space-between",
                gap:20, marginBottom:4, alignItems:"center"
              }}>
                <span style={{ fontSize:9, color:"#2d4a6e" }}>{sys}</span>
                <span style={{
                  fontSize:8, color:"#00e676",
                  letterSpacing:1
                }}>● {status}</span>
              </div>
            ))}
          </div>

          {/* Cursor blink bottom center */}
          <div style={{
            position:"absolute", bottom:16, left:"50%",
            transform:"translateX(-50%)", zIndex:999,
            fontSize:9, color:"#1a2332", letterSpacing:3,
            display:"flex", alignItems:"center", gap:6
          }}>
            HOVER HIGHWAYS FOR DETAILS
            <span style={{ animation:"blink 1s infinite" }}>_</span>
          </div>
        </div>
      </div>

      {/* Floating Chat Button */}
      <div style={{ position:"fixed", bottom:24, right:24, zIndex:2000 }}>
        {!chatOpen && (
          <button
            className="chat-fab"
            onClick={() => { setChatOpen(true); if(chatMsgs.length===0) {
              setChatMsgs([{ role:"bot", text:"Hey! Ask me about Indian highway risk, route safety, or freight disruptions. I only answer logistics questions." }]);
            }}}
            style={{
              width:56, height:56, borderRadius:"50%",
              background:"linear-gradient(135deg,#0055cc,#0077ff)",
              border:"none", cursor:"pointer",
              boxShadow:"0 0 0 0 #0077ff66",
              animation:"pulse-ring 2s infinite, sparkle-float 3s ease-in-out infinite",
              display:"flex", alignItems:"center", justifyContent:"center",
              fontSize:22, transition:"transform 0.2s",
              position:"relative"
            }}
          >
            💬
            {sparkle && (
              <div style={{
                position:"absolute", top:-4, right:-4,
                width:14, height:14, borderRadius:"50%",
                background:"#ffb800", fontSize:8,
                display:"flex", alignItems:"center", justifyContent:"center",
                animation:"slide-up 0.3s ease"
              }}>✦</div>
            )}
          </button>
        )}

        {chatOpen && (
          <div style={{
            width:360, height:480,
            background:"#0d1117",
            border:"1px solid #1a2332",
            borderRadius:8,
            display:"flex", flexDirection:"column",
            boxShadow:"0 24px 80px #000a",
            animation:"slide-up 0.3s ease"
          }}>
            {/* Chat Header */}
            <div style={{
              padding:"12px 16px",
              borderBottom:"1px solid #1a2332",
              display:"flex", alignItems:"center",
              justifyContent:"space-between",
              background:"#090d14",
              borderRadius:"8px 8px 0 0"
            }}>
              <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                <div style={{
                  width:32, height:32, borderRadius:"50%",
                  background:"linear-gradient(135deg,#0055cc,#0077ff)",
                  display:"flex", alignItems:"center",
                  justifyContent:"center", fontSize:14
                }}>🚛</div>
                <div>
                  <div style={{
                    fontSize:11, fontWeight:500,
                    color:"#e8f0fe", letterSpacing:1
                  }}>FREIGHT ASSISTANT</div>
                  <div style={{
                    fontSize:8, color:"#00e676",
                    letterSpacing:1.5
                  }}>● ONLINE — Groq + LangGraph</div>
                </div>
              </div>
              <button
                onClick={() => setChatOpen(false)}
                style={{
                  background:"transparent", border:"none",
                  color:"#4a5568", cursor:"pointer",
                  fontSize:16, lineHeight:1
                }}
              >✕</button>
            </div>

            {/* Messages */}
            <div style={{
              flex:1, overflow:"auto",
              padding:"12px", display:"flex",
              flexDirection:"column", gap:8
            }}>
              {chatMsgs.map((m,i) => (
                <div key={i} style={{
                  display:"flex",
                  justifyContent: m.role==="user" ? "flex-end" : "flex-start",
                  animation:"slide-up 0.2s ease"
                }}>
                  <div style={{
                    maxWidth:"82%",
                    padding:"8px 12px",
                    borderRadius: m.role==="user"
                      ? "10px 10px 2px 10px"
                      : "10px 10px 10px 2px",
                    background: m.role==="user"
                      ? "linear-gradient(135deg,#0055cc,#0077ff)"
                      : "#0f1823",
                    border: m.role==="bot" ? "1px solid #1a2332" : "none",
                    fontSize:11, lineHeight:1.6,
                    color: m.role==="user" ? "white" : "#c9d1e0"
                  }}>
                    {m.text}
                  </div>
                </div>
              ))}
              {chatLoading && (
                <div style={{ display:"flex", gap:4, padding:"4px 8px" }}>
                  {[0,1,2].map(i => (
                    <div key={i} style={{
                      width:5, height:5,
                      background:"#0077ff",
                      borderRadius:"50%",
                      animation:`dot-bounce 0.8s ease ${i*0.15}s infinite`
                    }}/>
                  ))}
                </div>
              )}
              <div ref={chatEndRef}/>
            </div>

            {/* Suggestions */}
            {chatMsgs.length <= 1 && (
              <div style={{
                padding:"0 12px 8px",
                display:"flex", flexWrap:"wrap", gap:4
              }}>
                {[
                  "Is NH-44 safe today?",
                  "Best route Hyderabad to Chennai",
                  "Any highway disruptions?",
                  "Compare NH-16 and NH-65"
                ].map(q => (
                  <button
                    key={q}
                    onClick={() => { setChatInput(q); }}
                    style={{
                      background:"#090d14",
                      border:"1px solid #1a2332",
                      borderRadius:3, padding:"4px 8px",
                      color:"#4a6080", cursor:"pointer",
                      fontSize:9, fontFamily:"'DM Mono',monospace",
                      letterSpacing:0.5
                    }}
                  >{q}</button>
                ))}
              </div>
            )}

            {/* Input */}
            <div style={{
              padding:"10px 12px",
              borderTop:"1px solid #1a2332",
              display:"flex", gap:8
            }}>
              <input
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => e.key==="Enter" && handleChat()}
                placeholder="Ask about routes, risk, disruptions..."
                style={{
                  flex:1, background:"#090d14",
                  border:"1px solid #1a2332",
                  borderRadius:4, padding:"7px 10px",
                  color:"#c9d1e0", fontSize:10,
                  outline:"none", fontFamily:"'DM Mono',monospace"
                }}
              />
              <button
                onClick={handleChat}
                disabled={chatLoading}
                style={{
                  background:"linear-gradient(135deg,#0055cc,#0077ff)",
                  border:"none", borderRadius:4,
                  padding:"7px 12px", cursor:"pointer",
                  fontSize:12
                }}
              >→</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}