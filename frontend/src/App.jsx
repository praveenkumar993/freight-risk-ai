import { useState, useEffect, useRef, useCallback } from "react";
import axios from "axios";
import {
  MapContainer, TileLayer, Polyline, Tooltip,
  CircleMarker, useMap, Marker, Popup
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import {
  PieChart, Pie, Cell, Tooltip as ReTooltip, Legend,
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  ResponsiveContainer, AreaChart, Area
} from "recharts";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

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

const CITY_COORDS = {
  "Delhi":[28.6139,77.2090],"Nagpur":[21.1458,79.0882],"Hyderabad":[17.3850,78.4867],
  "Bangalore":[12.9716,77.5946],"Chennai":[13.0827,80.2707],"Krishnagiri":[12.5186,78.2137],
  "Mumbai":[19.0760,72.8777],"Pune":[18.5204,73.8567],"Hubli":[15.3647,75.1240],
  "Vijayawada":[16.5062,80.6480],"Visakhapatnam":[17.6868,83.2185],"Nellore":[14.4426,79.9865],
  "Guntur":[16.3067,80.4365],"Mysore":[12.2958,76.6394],"Coimbatore":[11.0168,76.9558],
  "Kochi":[9.9312,76.2673],"Thrissur":[10.5276,76.2144],"Kozhikode":[11.2588,75.7804],
  "Thiruvananthapuram":[8.5241,76.9366],"Kurnool":[15.8281,78.0373],"Solapur":[17.6599,75.9064],
  "Warangal":[17.9784,79.5941],"Salem":[11.6643,78.1460],"Madurai":[9.9252,78.1198],
  "Tiruchirappalli":[10.7905,78.7047],"Tirupati":[13.6288,79.4192],"Kadapa":[14.4674,78.8241],
};

const CITIES = Object.keys(CITY_COORDS);
const PRODUCTS = ["Electronics","Pharmaceuticals","Food & Perishables","Automotive Parts","Textiles","Industrial Machinery","FMCG","Chemicals","Construction Materials"];

// Always get today's date in YYYY-MM-DD format (local time, not UTC)
const getTodayStr = () => {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm   = String(d.getMonth()+1).padStart(2,"0");
  const dd   = String(d.getDate()).padStart(2,"0");
  return `${yyyy}-${mm}-${dd}`;
};

// New color palette — deep teal/amber/crimson theme
const COLORS = {
  high: "#ff4d6d",
  medium: "#ffb703",
  low: "#06d6a0",
  primary: "#00b4d8",
  accent: "#f72585",
  purple: "#7b2d8b",
  bg: "#050b18",
  surface: "#080f1f",
  card: "#0b1425",
  border: "#0e2040",
  border2: "#142850",
  text: "#e8f4fd",
  muted: "#4a7aa0",
  dim: "#1e3a5f",
};

const RC = { HIGH: COLORS.high, MEDIUM: COLORS.medium, LOW: COLORS.low };
const RL = l => RC[l] || RC.LOW;
const fmt = n => typeof n === 'number' ? n.toFixed(1) : n;
const fmtCurrency = n => typeof n === 'number' ? `₹${n.toLocaleString('en-IN')}` : n;

const GUARDRAIL = [
  // highways & roads
  "highway","route","risk","freight","truck","transport","road","nh-","nh44","nh48","nh16","nh65","nh275","nh30","nh340","nh544",
  // events
  "disruption","flood","rain","monsoon","strike","accident","landslide","cyclone","congestion","delay",
  // logistics
  "shipment","logistics","cargo","delivery","cost","toll","fuel","driver",
  // cities covered
  "bangalore","hyderabad","chennai","mumbai","delhi","pune","kochi","vijayawada","coimbatore",
  "nagpur","visakhapatnam","nellore","guntur","mysore","thrissur","kozhikode","warangal","salem",
  "madurai","tiruchirappalli","tirupati","kadapa","kurnool","solapur","hubli","krishnagiri",
  // risk terms
  "safe","dangerous","score","weather","traffic","condition","south india",
  // project-specific questions
  "source","destination","origin","product","quantity","analyze","analysis","segment","corridor",
  "primary","alternate","shap","model","ensemble","xgboost","lightgbm","randomforest","mlflow",
  "kafka","spark","airflow","prediction","probability","mitigation","recommendation",
  // natural questions about the app/shipment
  "what is my","what are my","current","selected","set","configured","which city","which route",
  "tell me","show me","explain","how much","how long","distance","duration","km","hours",
];
const isFreight = msg => {
  const lower = msg.toLowerCase();
  return GUARDRAIL.some(k => lower.includes(k));
};

// Map fly-to component
function FlyToRoute({ coords }) {
  const map = useMap();
  useEffect(() => {
    if (coords && coords.length >= 2) {
      const lats = coords.map(c => c[0]);
      const lngs = coords.map(c => c[1]);
      const bounds = [[Math.min(...lats)-0.5, Math.min(...lngs)-0.5],[Math.max(...lats)+0.5, Math.max(...lngs)+0.5]];
      map.flyToBounds(bounds, { duration: 1.5, padding: [60,60] });
    }
  }, [coords]);
  return null;
}

function RiskBadge({ level, score }) {
  const c = RL(level);
  return (
    <span style={{
      display:"inline-flex", alignItems:"center", gap:5,
      background:`${c}18`, color:c,
      padding:"3px 10px", borderRadius:20,
      fontSize:10, fontWeight:700, letterSpacing:0.8,
      border:`1px solid ${c}50`,
      textTransform:"uppercase"
    }}>
      <span style={{ width:5, height:5, borderRadius:"50%", background:c, display:"inline-block", boxShadow:`0 0 6px ${c}` }}/>
      {level}{score !== undefined && ` · ${fmt(score)}`}
    </span>
  );
}

function StatCard({ label, value, sub, color=COLORS.primary, icon }) {
  return (
    <div style={{
      background:`linear-gradient(135deg, ${COLORS.card} 0%, ${color}08 100%)`,
      borderRadius:14, padding:"18px 20px",
      border:`1px solid ${color}25`,
      flex:1, position:"relative", overflow:"hidden",
      transition:"transform 0.2s, box-shadow 0.2s",
    }} onMouseEnter={e=>{e.currentTarget.style.transform="translateY(-2px)";e.currentTarget.style.boxShadow=`0 12px 40px ${color}20`}}
       onMouseLeave={e=>{e.currentTarget.style.transform="";e.currentTarget.style.boxShadow=""}}>
      <div style={{ position:"absolute", top:-20, right:-20, width:80, height:80, borderRadius:"50%", background:`${color}08` }}/>
      <div style={{ fontSize:20, marginBottom:8 }}>{icon}</div>
      <div style={{ fontSize:9, color:COLORS.muted, letterSpacing:2, marginBottom:6, textTransform:"uppercase" }}>{label}</div>
      <div style={{ fontSize:26, fontWeight:800, color, lineHeight:1, fontFamily:"'Space Grotesk',sans-serif" }}>{value}</div>
      {sub && <div style={{ fontSize:10, color:COLORS.muted, marginTop:6 }}>{sub}</div>}
    </div>
  );
}

function ProgressBar({ value, max=100, color=COLORS.primary, height=4 }) {
  return (
    <div style={{ background:COLORS.dim, borderRadius:height, height, overflow:"hidden" }}>
      <div style={{
        width:`${Math.min((value/max)*100,100)}%`, height:"100%",
        background:`linear-gradient(90deg, ${color}cc, ${color})`,
        borderRadius:height, transition:"width 1s ease",
        boxShadow:`0 0 8px ${color}60`
      }}/>
    </div>
  );
}

// Mini Donut for inline use
function MiniDonut({ high, medium, low, size=80 }) {
  const data = [
    { name:"High", value:high, color:COLORS.high },
    { name:"Med", value:medium, color:COLORS.medium },
    { name:"Low", value:low, color:COLORS.low },
  ].filter(d => d.value > 0);
  return (
    <PieChart width={size} height={size}>
      <Pie data={data} cx={size/2-1} cy={size/2-1} innerRadius={size*0.28} outerRadius={size*0.44}
        dataKey="value" stroke="none">
        {data.map((d,i) => <Cell key={i} fill={d.color}/>)}
      </Pie>
    </PieChart>
  );
}

export default function App() {
  const [highways, setHighways] = useState([]);
  const [segments, setSegments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("dashboard");
  const [analyzeTab, setAnalyzeTab] = useState("form");
  const [form, setForm] = useState({
    origin:"Hyderabad", destination:"Chennai",
    product_type:"Electronics", quantity_kg:500,
    transport_mode:"Road", expected_date:getTodayStr()
  });
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatMsgs, setChatMsgs] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [pulse, setPulse] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [routeCoords, setRouteCoords] = useState(null);
  const chatEnd = useRef(null);

  useEffect(() => { fetchAll(); }, []);
  useEffect(() => { chatEnd.current?.scrollIntoView({ behavior:"smooth" }); }, [chatMsgs]);
  useEffect(() => {
    const t = setInterval(() => setPulse(p => !p), 1500);
    return () => clearInterval(t);
  }, []);

  const fetchAll = async () => {
    try {
      setLoading(true);
      const [hw, seg] = await Promise.all([
        axios.get(`${API}/highway-risk`),
        axios.get(`${API}/segments`)
      ]);
      setHighways(hw.data);
      setSegments(seg.data);
      setLastRefresh(new Date());
    } catch(e) { console.error(e); }
    finally { setLoading(false); }
  };

  const handleAnalyze = async () => {
    try {
      setAnalyzing(true);
      setResult(null);
      setRouteCoords(null);
      const res = await axios.post(`${API}/analyze`, form);
      setResult(res.data);
      setAnalyzeTab("result");
      // Build route coords for zoom
      const path = res.data?.primary_route?.path || [];
      const coords = path.map(c => CITY_COORDS[c]).filter(Boolean);
      if (coords.length >= 2) setRouteCoords(coords);
    } catch(e) { console.error(e); }
    finally { setAnalyzing(false); }
  };

  const handleChat = async () => {
    if (!chatInput.trim()) return;
    const msg = chatInput.trim();
    setChatInput("");

    // Answer shipment config questions locally without needing the backend
    const lower = msg.toLowerCase();
    const isConfigQ =
      lower.includes("source") || lower.includes("origin") ||
      lower.includes("destination") || lower.includes("product") ||
      lower.includes("quantity") || lower.includes("date") ||
      lower.includes("what is my") || lower.includes("what are my") ||
      lower.includes("selected") || lower.includes("configured") ||
      lower.includes("current shipment") || lower.includes("my shipment");

    if (isConfigQ) {
      const resultSnippet = result
        ? ` The last analysis showed a risk score of ${result.risk_score?.toFixed(1)} (${result.risk_level}) with a ${result.delay_probability?.toFixed(1)}% delay probability.`
        : " No analysis has been run yet — click ⚡ Analyze Risk to get a full assessment.";
      setChatMsgs(p => [...p,
        { role:"user", text:msg },
        { role:"bot", text:
          `Here's your current shipment configuration:\n\n` +
          `📍 Origin: ${form.origin}\n` +
          `🏁 Destination: ${form.destination}\n` +
          `📦 Product: ${form.product_type}\n` +
          `⚖ Quantity: ${form.quantity_kg} kg\n` +
          `🚛 Mode: ${form.transport_mode}\n` +
          `📅 Date: ${form.expected_date}` +
          resultSnippet
        }
      ]);
      return;
    }

    if (!isFreight(msg)) {
      setChatMsgs(p => [...p,
        { role:"user", text:msg },
        { role:"bot", text:"I'm specialized in Indian highway freight risk. Ask me about route safety, disruptions, highway conditions, your shipment details, or logistics planning." }
      ]);
      return;
    }

    setChatMsgs(p => [...p, { role:"user", text:msg }]);
    setChatLoading(true);
    try {
      // Build rich context to send alongside the message
      const context = {
        current_shipment: {
          origin: form.origin,
          destination: form.destination,
          product_type: form.product_type,
          quantity_kg: form.quantity_kg,
          transport_mode: form.transport_mode,
          expected_date: form.expected_date,
        },
        last_analysis: result ? {
          risk_score: result.risk_score,
          risk_level: result.risk_level,
          delay_probability: result.delay_probability,
          expected_delay_days: result.expected_delay_days,
          root_cause: result.root_cause,
          primary_route: result.primary_route?.path?.join(" → "),
          alternate_route: result.alternate_route?.path?.join(" → "),
        } : null,
      };
      const res = await axios.post(`${API}/chat`, {
        message: msg,
        context,   // backend can use this if it supports it; ignored gracefully if not
      });
      setChatMsgs(p => [...p, { role:"bot", text:res.data.response }]);
    } catch(e) {
      setChatMsgs(p => [...p, { role:"bot", text:"Backend error. Ensure FastAPI is running on port 8000." }]);
    } finally { setChatLoading(false); }
  };

  const highRisk = highways.filter(h => h.risk_level==="HIGH").length;
  const medRisk  = highways.filter(h => h.risk_level==="MEDIUM").length;
  const lowRisk  = highways.filter(h => h.risk_level==="LOW").length;
  const avgRisk  = highways.length ? (highways.reduce((a,h) => a + (h.risk_score||0), 0) / highways.length).toFixed(1) : 0;

  // Pie data
  const riskPieData = [
    { name:"High Risk", value:highRisk, color:COLORS.high },
    { name:"Medium Risk", value:medRisk, color:COLORS.medium },
    { name:"Low Risk", value:lowRisk, color:COLORS.low },
  ];

  const segPieData = (() => {
    const h = segments.filter(s=>s.risk_level==="HIGH").length;
    const m = segments.filter(s=>s.risk_level==="MEDIUM").length;
    const l = segments.filter(s=>s.risk_level==="LOW").length;
    return [
      { name:"High", value:h, color:COLORS.high },
      { name:"Medium", value:m, color:COLORS.medium },
      { name:"Safe", value:l, color:COLORS.low },
    ];
  })();

  const navItems = [
    { id:"dashboard", label:"Dashboard", icon:"⬡" },
    { id:"analyze",   label:"Analyze Route", icon:"◈" },
    { id:"analytics", label:"Analytics", icon:"◉" },
    { id:"pipeline",  label:"Pipeline", icon:"◫" },
  ];

  return (
    <div style={{ fontFamily:"'Syne','Space Grotesk',sans-serif", background:COLORS.bg, minHeight:"100vh", color:COLORS.text }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
        * { box-sizing:border-box; margin:0; padding:0; }
        ::-webkit-scrollbar { width:4px; height:4px; }
        ::-webkit-scrollbar-track { background:transparent; }
        ::-webkit-scrollbar-thumb { background:${COLORS.border2}; border-radius:2px; }
        select, input { font-family:'Space Grotesk',sans-serif !important; color-scheme:dark; }
        option { background:${COLORS.card}; }
        @keyframes fadeUp { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }
        @keyframes fadeIn { from { opacity:0; } to { opacity:1; } }
        @keyframes spin { to { transform:rotate(360deg); } }
        @keyframes dot { 0%,80%,100% { transform:scale(0.6); opacity:0.4; } 40% { transform:scale(1); opacity:1; } }
        @keyframes glow { 0%,100% { box-shadow:0 0 0 0 rgba(0,180,216,0.5); } 50% { box-shadow:0 0 0 8px rgba(0,180,216,0); } }
        @keyframes float { 0%,100% { transform:translateY(0); } 50% { transform:translateY(-8px); } }
        @keyframes shimmer { 0% { background-position:200% 0; } 100% { background-position:-200% 0; } }
        @keyframes ping { 0% { transform:scale(1); opacity:1; } 75%,100% { transform:scale(2); opacity:0; } }
        @keyframes scanline { 0% { transform:translateY(-100%); } 100% { transform:translateY(100vh); } }
        .hw-card:hover { background:${COLORS.dim}22 !important; transform:translateX(4px); }
        .nav-btn { position:relative; overflow:hidden; }
        .nav-btn::after { content:''; position:absolute; inset:0; background:linear-gradient(90deg,transparent,rgba(0,180,216,0.08),transparent); transform:translateX(-100%); transition:transform 0.4s; }
        .nav-btn:hover::after { transform:translateX(100%); }
        .analyze-btn:hover:not(:disabled) { transform:translateY(-2px); box-shadow:0 12px 30px ${COLORS.primary}40 !important; }
        .seg-row:hover { background:${COLORS.dim}30 !important; }
        .quick-q:hover { background:${COLORS.dim} !important; color:${COLORS.primary} !important; border-color:${COLORS.primary}50 !important; }
        .stat-card-hover:hover { transform:translateY(-3px); }
        .leaflet-container { background:#020918; }
        .leaflet-tooltip { background:${COLORS.card}f0 !important; border:1px solid ${COLORS.border2} !important; color:${COLORS.text} !important; border-radius:8px !important; font-family:'Space Grotesk',sans-serif !important; backdrop-filter:blur(8px); }
        .leaflet-tooltip::before { display:none; }
      `}</style>

      {/* === HEADER === */}
      <header style={{
        background:`${COLORS.surface}f0`, backdropFilter:"blur(16px)",
        borderBottom:`1px solid ${COLORS.border2}`,
        padding:"0 28px", height:60,
        display:"flex", alignItems:"center", justifyContent:"space-between",
        position:"sticky", top:0, zIndex:100
      }}>
        {/* Logo */}
        <div style={{ display:"flex", alignItems:"center", gap:14 }}>
          <div style={{
            width:38, height:38, borderRadius:10,
            background:`linear-gradient(135deg, ${COLORS.primary}, #0077b6)`,
            display:"flex", alignItems:"center", justifyContent:"center",
            fontSize:18, boxShadow:`0 0 20px ${COLORS.primary}50`,
            position:"relative"
          }}>
            🛣
            <div style={{ position:"absolute", inset:-2, borderRadius:12, border:`1px solid ${COLORS.primary}40`, animation:"glow 3s infinite" }}/>
          </div>
          <div>
            <div style={{ fontSize:16, fontWeight:800, color:COLORS.text, letterSpacing:1, fontFamily:"'Syne',sans-serif" }}>
              FREIGHT<span style={{ color:COLORS.primary }}>RISK</span> AI
            </div>
            <div style={{ fontSize:9, color:COLORS.muted, letterSpacing:2, textTransform:"uppercase" }}>India Highway Intelligence</div>
          </div>
        </div>

        {/* Nav */}
        <nav style={{ display:"flex", gap:4, background:`${COLORS.card}80`, borderRadius:10, padding:4, border:`1px solid ${COLORS.border}` }}>
          {navItems.map(({ id, label, icon }) => {
            const active = tab === id;
            return (
              <button key={id} className="nav-btn" onClick={() => setTab(id)} style={{
                padding:"8px 20px", borderRadius:7, border:"none", cursor:"pointer",
                fontSize:12, fontWeight:600, letterSpacing:0.5, transition:"all 0.2s",
                fontFamily:"'Space Grotesk',sans-serif",
                background: active ? `linear-gradient(135deg, ${COLORS.primary}30, ${COLORS.primary}15)` : "transparent",
                color: active ? COLORS.primary : COLORS.muted,
                borderBottom: active ? `2px solid ${COLORS.primary}` : "2px solid transparent",
                display:"flex", alignItems:"center", gap:6
              }}>
                <span style={{ fontSize:11 }}>{icon}</span>{label}
              </button>
            );
          })}
        </nav>

        {/* Live indicator */}
        <div style={{ display:"flex", alignItems:"center", gap:12 }}>
          <div style={{ display:"flex", alignItems:"center", gap:8, fontSize:11, color:COLORS.muted }}>
            <div style={{ position:"relative", width:10, height:10 }}>
              <div style={{ width:10, height:10, borderRadius:"50%", background:COLORS.low }}/>
              <div style={{ position:"absolute", inset:0, borderRadius:"50%", background:COLORS.low, animation:"ping 2s infinite" }}/>
            </div>
            <span style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:10 }}>
              LIVE · {lastRefresh.toLocaleTimeString()}
            </span>
          </div>
          <button onClick={fetchAll} style={{
            background:`${COLORS.card}`, border:`1px solid ${COLORS.border2}`,
            borderRadius:8, padding:"6px 14px", color:COLORS.muted, cursor:"pointer",
            fontSize:11, display:"flex", alignItems:"center", gap:6,
            fontFamily:"'Space Grotesk',sans-serif", transition:"all 0.2s"
          }}
          onMouseEnter={e=>{e.currentTarget.style.borderColor=COLORS.primary;e.currentTarget.style.color=COLORS.primary}}
          onMouseLeave={e=>{e.currentTarget.style.borderColor=COLORS.border2;e.currentTarget.style.color=COLORS.muted}}>
            ↻ Refresh
          </button>
        </div>
      </header>

      {/* ======== DASHBOARD TAB ======== */}
      {tab === "dashboard" && (
        <div style={{ display:"flex", height:"calc(100vh - 60px)" }}>
          {/* Sidebar */}
          <div style={{
            width:360, background:COLORS.surface, borderRight:`1px solid ${COLORS.border2}`,
            display:"flex", flexDirection:"column", overflow:"hidden"
          }}>
            {/* Pie + Stats row */}
            <div style={{ padding:"16px 16px 0" }}>
              <div style={{ display:"flex", alignItems:"center", gap:12, background:COLORS.card, borderRadius:14, padding:14, border:`1px solid ${COLORS.border2}`, marginBottom:12 }}>
                <MiniDonut high={highRisk} medium={medRisk} low={lowRisk} size={90}/>
                <div style={{ flex:1 }}>
                  {[
                    { label:"HIGH RISK", val:highRisk, color:COLORS.high },
                    { label:"MEDIUM", val:medRisk, color:COLORS.medium },
                    { label:"SAFE", val:lowRisk, color:COLORS.low },
                  ].map(s => (
                    <div key={s.label} style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:7 }}>
                      <div style={{ display:"flex", alignItems:"center", gap:6 }}>
                        <div style={{ width:8, height:8, borderRadius:2, background:s.color }}/>
                        <span style={{ fontSize:9, color:COLORS.muted, letterSpacing:1.2 }}>{s.label}</span>
                      </div>
                      <span style={{ fontSize:20, fontWeight:800, color:s.color, fontFamily:"'Syne',sans-serif" }}>{s.val}</span>
                    </div>
                  ))}
                  <div style={{ borderTop:`1px solid ${COLORS.border}`, paddingTop:7, display:"flex", justifyContent:"space-between" }}>
                    <span style={{ fontSize:9, color:COLORS.muted }}>AVG SCORE</span>
                    <span style={{ fontSize:14, fontWeight:700, color:COLORS.primary, fontFamily:"'Syne',sans-serif" }}>{avgRisk}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Highway Cards */}
            <div style={{ flex:1, overflow:"auto", padding:"0 12px 12px" }}>
              <div style={{ fontSize:9, color:COLORS.muted, letterSpacing:2.5, marginBottom:10, marginTop:4, textTransform:"uppercase" }}>
                Highway Corridors
              </div>
              {loading ? (
                <div style={{ textAlign:"center", padding:40, color:COLORS.dim }}>
                  <div style={{ width:24, height:24, border:`2px solid ${COLORS.dim}`, borderTop:`2px solid ${COLORS.primary}`, borderRadius:"50%", margin:"0 auto 10px", animation:"spin 0.8s linear infinite" }}/>
                  <div style={{ fontSize:11 }}>Fetching live data...</div>
                </div>
              ) : highways.map((hw,i) => (
                <div key={hw.highway} className="hw-card" style={{
                  background:COLORS.card, borderRadius:12, padding:"13px 14px",
                  marginBottom:8, border:`1px solid ${RL(hw.risk_level)}18`,
                  borderLeft:`3px solid ${RL(hw.risk_level)}`,
                  transition:"all 0.2s", cursor:"default",
                  animation:`fadeUp 0.3s ease ${i*0.05}s both`
                }}>
                  <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:8 }}>
                    <div>
                      <div style={{ fontSize:14, fontWeight:700, color:COLORS.text, fontFamily:"'Syne',sans-serif" }}>{hw.highway}</div>
                      <div style={{ fontSize:10, color:COLORS.muted, marginTop:2 }}>{hw.weather_summary}</div>
                    </div>
                    <RiskBadge level={hw.risk_level} score={hw.risk_score} />
                  </div>
                  <ProgressBar value={hw.risk_score||0} color={RL(hw.risk_level)} height={3}/>
                  <div style={{ display:"flex", justifyContent:"space-between", marginTop:7, fontSize:10, color:COLORS.muted }}>
                    <span>{hw.recommendation}</span>
                    <span style={{ color:`${RL(hw.risk_level)}bb`, fontFamily:"'JetBrains Mono',monospace" }}>
                      {(hw.risk_score||0).toFixed(1)}/100
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {/* Pipeline Status */}
            <div style={{ padding:"12px 14px", borderTop:`1px solid ${COLORS.border2}` }}>
              <div style={{ fontSize:9, color:COLORS.muted, letterSpacing:2.5, marginBottom:8, textTransform:"uppercase" }}>Pipeline Status</div>
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:6 }}>
                {[
                  ["Kafka","Streaming",COLORS.low],
                  ["Spark","Active",COLORS.primary],
                  ["Airflow","Scheduled",COLORS.medium],
                  ["Ensemble ML","Running","#c77dff"],
                ].map(([sys,status,color]) => (
                  <div key={sys} style={{
                    background:COLORS.bg, borderRadius:8, padding:"8px 10px",
                    border:`1px solid ${color}20`, display:"flex", alignItems:"center", gap:7
                  }}>
                    <div style={{ width:6, height:6, borderRadius:"50%", background:color, boxShadow:`0 0 8px ${color}`, flexShrink:0 }}/>
                    <div>
                      <div style={{ fontSize:10, color:COLORS.text, fontWeight:600 }}>{sys}</div>
                      <div style={{ fontSize:8, color, letterSpacing:0.5 }}>{status}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Map */}
          <div style={{ flex:1, position:"relative" }}>
            <MapContainer center={[16,78]} zoom={6} style={{ height:"100%", width:"100%" }} zoomControl={false}>
              <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" attribution=""/>

              {/* Highway corridors — dotted cyan lines */}
              {highways.map(hw => (
                HIGHWAY_COORDS[hw.highway] && (
                  <Polyline key={hw.highway}
                    positions={HIGHWAY_COORDS[hw.highway]}
                    pathOptions={{
                      color: "#00b4d8",
                      weight: hw.risk_level==="HIGH" ? 3 : 2,
                      opacity: 0.7,
                      dashArray: "8 6",
                      dashOffset: "0"
                    }}
                  >
                    <Tooltip sticky>
                      <div style={{ fontFamily:"'Space Grotesk',sans-serif", fontSize:12 }}>
                        <strong style={{ color:COLORS.primary }}>{hw.highway}</strong><br/>
                        Risk: <span style={{ color:RL(hw.risk_level) }}>{hw.risk_level}</span> · Score: {(hw.risk_score||0).toFixed(1)}<br/>
                        {hw.weather_summary}<br/>
                        <em style={{ color:RL(hw.risk_level) }}>{hw.recommendation}</em>
                      </div>
                    </Tooltip>
                  </Polyline>
                )
              ))}

              {/* City markers for risky segments */}
              {segments.filter(s => s.risk_level==="HIGH"||s.risk_level==="MEDIUM").map((seg,i) => {
                const coord = CITY_COORDS[seg.origin];
                if (!coord) return null;
                return (
                  <CircleMarker key={i} center={coord}
                    radius={seg.risk_level==="HIGH" ? 8 : 5}
                    pathOptions={{ color:RL(seg.risk_level), fillColor:RL(seg.risk_level), fillOpacity:0.35, weight:2 }}
                  >
                    <Tooltip>
                      <div style={{ fontSize:11 }}>
                        <strong>{seg.segment}</strong><br/>
                        Risk: {seg.risk_level} · {seg.risk_score?.toFixed(1)}
                      </div>
                    </Tooltip>
                  </CircleMarker>
                );
              })}
            </MapContainer>

            {/* Legend */}
            <div style={{
              position:"absolute", bottom:20, left:20, zIndex:999,
              background:`${COLORS.bg}ee`, borderRadius:12,
              padding:"14px 18px", border:`1px solid ${COLORS.border2}`,
              backdropFilter:"blur(12px)", animation:"fadeIn 0.5s ease"
            }}>
              <div style={{ fontSize:9, color:COLORS.muted, letterSpacing:2.5, marginBottom:10, textTransform:"uppercase" }}>Risk Level</div>
              {[["HIGH",COLORS.high,"Avoid"],["MEDIUM",COLORS.medium,"Caution"],["LOW",COLORS.low,"Safe"]].map(([l,c,d]) => (
                <div key={l} style={{ display:"flex", alignItems:"center", gap:8, marginBottom:5 }}>
                  <div style={{ width:22, height:2, background:c, borderRadius:2, boxShadow:`0 0 6px ${c}` }}/>
                  <span style={{ fontSize:10, color:COLORS.text, fontWeight:600 }}>{l}</span>
                  <span style={{ fontSize:9, color:COLORS.muted }}>— {d}</span>
                </div>
              ))}
              <div style={{ borderTop:`1px solid ${COLORS.border}`, marginTop:8, paddingTop:8 }}>
                <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:3 }}>
                  <div style={{ width:22, borderTop:`2px dashed ${COLORS.primary}`, opacity:0.8 }}/>
                  <span style={{ fontSize:9, color:COLORS.muted }}>Highway corridor</span>
                </div>
              </div>
            </div>

            {/* Coverage info */}
            <div style={{
              position:"absolute", top:16, right:16, zIndex:999,
              background:`${COLORS.bg}ee`, borderRadius:12,
              padding:"14px 18px", border:`1px solid ${COLORS.border2}`,
              backdropFilter:"blur(12px)", minWidth:170
            }}>
              <div style={{ fontSize:9, color:COLORS.muted, letterSpacing:2.5, marginBottom:10, textTransform:"uppercase" }}>Coverage</div>
              {[["Highways",highways.length],["Segments",segments.length],["Cities","35+"],["States","8"]].map(([l,v]) => (
                <div key={l} style={{ display:"flex", justifyContent:"space-between", marginBottom:6 }}>
                  <span style={{ fontSize:10, color:COLORS.muted }}>{l}</span>
                  <span style={{ fontSize:11, color:COLORS.primary, fontWeight:700, fontFamily:"'JetBrains Mono',monospace" }}>{v}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ======== ANALYZE TAB ======== */}
      {tab === "analyze" && (
        <div style={{ display:"flex", height:"calc(100vh - 60px)" }}>
          {/* Form Panel */}
          <div style={{ width:360, background:COLORS.surface, borderRight:`1px solid ${COLORS.border2}`, display:"flex", flexDirection:"column" }}>
            {/* Sub tabs */}
            <div style={{ display:"flex", borderBottom:`1px solid ${COLORS.border2}` }}>
              {[["form","⚙ Configure"],["result","◈ Results"]].map(([id,label]) => (
                <button key={id} onClick={() => setAnalyzeTab(id)} style={{
                  flex:1, padding:"14px", border:"none", cursor:"pointer",
                  background: analyzeTab===id ? `${COLORS.primary}12` : "transparent",
                  color: analyzeTab===id ? COLORS.primary : COLORS.muted,
                  fontSize:12, fontWeight:600, fontFamily:"'Space Grotesk',sans-serif",
                  borderBottom: analyzeTab===id ? `2px solid ${COLORS.primary}` : "2px solid transparent",
                  transition:"all 0.2s"
                }}>{label}</button>
              ))}
            </div>

            <div style={{ flex:1, overflow:"auto", padding:18 }}>
              {analyzeTab === "form" && (
                <div style={{ animation:"fadeUp 0.3s ease" }}>
                  <div style={{ fontSize:9, color:COLORS.muted, letterSpacing:2.5, marginBottom:16, textTransform:"uppercase" }}>Shipment Parameters</div>
                  {[
                    { label:"Origin City", key:"origin", type:"select", opts:CITIES },
                    { label:"Destination City", key:"destination", type:"select", opts:CITIES },
                    { label:"Product Type", key:"product_type", type:"select", opts:PRODUCTS },
                    { label:"Transport Mode", key:"transport_mode", type:"select", opts:["Road"] },
                    { label:"Expected Date", key:"expected_date", type:"date" },
                    { label:"Quantity (kg)", key:"quantity_kg", type:"number" },
                  ].map(f => (
                    <div key={f.key} style={{ marginBottom:14 }}>
                      <label style={{ fontSize:10, color:COLORS.muted, display:"block", marginBottom:6, letterSpacing:0.8, textTransform:"uppercase" }}>{f.label}</label>
                      {f.type === "select" ? (
                        <select value={form[f.key]} onChange={e => setForm(p=>({...p,[f.key]:e.target.value}))} style={{
                          width:"100%", background:COLORS.card, border:`1px solid ${COLORS.border2}`,
                          borderRadius:9, padding:"10px 14px", color:COLORS.text, fontSize:12, outline:"none",
                          transition:"border-color 0.2s"
                        }}
                        onFocus={e=>e.target.style.borderColor=COLORS.primary}
                        onBlur={e=>e.target.style.borderColor=COLORS.border2}>
                          {f.opts.map(o => <option key={o}>{o}</option>)}
                        </select>
                      ) : (
                        <input
                          type={f.type}
                          value={form[f.key]}
                          min={f.type==="date" ? getTodayStr() : undefined}
                          onChange={e => setForm(p=>({
                            ...p, [f.key]: f.type==="number" ? parseFloat(e.target.value)||0 : e.target.value
                          }))}
                          style={{
                            width:"100%", background:COLORS.card, border:`1px solid ${COLORS.border2}`,
                            borderRadius:9, padding:"10px 14px", color:COLORS.text, fontSize:12, outline:"none",
                            transition:"border-color 0.2s"
                          }}
                          onFocus={e=>e.target.style.borderColor=COLORS.primary}
                          onBlur={e=>e.target.style.borderColor=COLORS.border2}
                        />
                      )}
                    </div>
                  ))}
                  <button className="analyze-btn" onClick={handleAnalyze} disabled={analyzing} style={{
                    width:"100%", padding:14, marginTop:10,
                    background: analyzing ? COLORS.border2 : `linear-gradient(135deg, ${COLORS.primary}, #0077b6)`,
                    border:"none", borderRadius:10, color:"white", fontSize:13,
                    fontWeight:700, cursor: analyzing ? "not-allowed" : "pointer",
                    transition:"all 0.25s", display:"flex", alignItems:"center", justifyContent:"center", gap:10,
                    fontFamily:"'Syne',sans-serif", letterSpacing:0.5,
                    boxShadow: analyzing ? "none" : `0 4px 20px ${COLORS.primary}40`
                  }}>
                    {analyzing ? (
                      <><div style={{ width:16, height:16, border:"2px solid rgba(255,255,255,0.3)", borderTop:"2px solid white", borderRadius:"50%", animation:"spin 0.8s linear infinite" }}/> Analyzing Route...</>
                    ) : <>⚡ Analyze Risk</>}
                  </button>
                </div>
              )}

              {analyzeTab === "result" && !result && (
                <div style={{ textAlign:"center", padding:"70px 20px", color:COLORS.muted }}>
                  <div style={{ fontSize:48, marginBottom:14 }}>◈</div>
                  <div style={{ fontSize:13, marginBottom:16 }}>Run an analysis to see results</div>
                  <button onClick={() => setAnalyzeTab("form")} style={{
                    background:COLORS.card, border:`1px solid ${COLORS.border2}`,
                    borderRadius:8, padding:"8px 18px", color:COLORS.muted, cursor:"pointer", fontSize:11
                  }}>Configure Shipment →</button>
                </div>
              )}

              {analyzeTab === "result" && result && (
                <div style={{ animation:"fadeUp 0.3s ease" }}>
                  {/* Risk score card */}
                  <div style={{
                    background:`linear-gradient(135deg, ${RL(result.risk_level)}12, ${RL(result.risk_level)}05)`,
                    border:`1px solid ${RL(result.risk_level)}35`, borderRadius:14,
                    padding:18, marginBottom:14, position:"relative", overflow:"hidden"
                  }}>
                    <div style={{ position:"absolute", top:-30, right:-30, width:100, height:100, borderRadius:"50%", background:`${RL(result.risk_level)}08` }}/>
                    <div style={{ fontSize:9, color:COLORS.muted, letterSpacing:2.5, marginBottom:8, textTransform:"uppercase" }}>Risk Assessment</div>
                    <div style={{ display:"flex", alignItems:"baseline", gap:8, marginBottom:6 }}>
                      <span style={{ fontSize:52, fontWeight:800, color:RL(result.risk_level), lineHeight:1, fontFamily:"'Syne',sans-serif" }}>
                        {fmt(result.risk_score)}
                      </span>
                      <span style={{ fontSize:16, color:COLORS.muted }}>/100</span>
                      <RiskBadge level={result.risk_level} />
                    </div>
                    <div style={{ display:"flex", gap:20, marginTop:6 }}>
                      <div style={{ fontSize:11, color:COLORS.muted }}>
                        Delay prob <span style={{ color:COLORS.text, fontWeight:700 }}>{fmt(result.delay_probability)}%</span>
                      </div>
                      <div style={{ fontSize:11, color:COLORS.muted }}>
                        Impact <span style={{ color:COLORS.text, fontWeight:700 }}>+{result.expected_delay_days}d</span>
                      </div>
                    </div>
                  </div>

                  {/* Root Cause */}
                  <div style={{ background:COLORS.card, borderRadius:10, padding:14, marginBottom:12, border:`1px solid ${COLORS.border2}` }}>
                    <div style={{ fontSize:9, color:COLORS.muted, letterSpacing:2.5, marginBottom:8, textTransform:"uppercase" }}>Root Cause</div>
                    <div style={{ fontSize:11, color:"#cfe2f3", lineHeight:1.8 }}>{result.root_cause}</div>
                  </div>

                  {/* Routes */}
                  {[
                    { data:result.primary_route, cost:result.primary_cost, label:"PRIMARY ROUTE", color:COLORS.primary },
                    { data:result.alternate_route, cost:result.alternate_cost, label:"ALTERNATE ROUTE", color:COLORS.medium }
                  ].map(({ data, cost, label, color }) => data && (
                    <div key={label} style={{
                      background:COLORS.card, borderRadius:10, padding:14, marginBottom:10,
                      borderLeft:`3px solid ${color}`, border:`1px solid ${COLORS.border2}`,
                      borderLeftColor:color, borderLeftWidth:3
                    }}>
                      <div style={{ fontSize:9, color, letterSpacing:2, marginBottom:8, fontWeight:700, textTransform:"uppercase" }}>{label}</div>
                      <div style={{ display:"flex", gap:14, fontSize:11, color:COLORS.muted, marginBottom:8 }}>
                        <span>⏱ {data.duration_hours}hrs</span>
                        <span>📍 {data.distance_km}km</span>
                        <RiskBadge level={data.risk_level} />
                      </div>
                      <div style={{ fontSize:10, color:COLORS.muted, lineHeight:2, marginBottom:6 }}>
                        {data.path?.join(" → ")}
                      </div>
                      <div style={{ fontSize:10, color:`${color}99` }}>via {data.highways?.join(" + ")}</div>
                      {cost && (
                        <div style={{ marginTop:10, paddingTop:10, borderTop:`1px solid ${COLORS.border}` }}>
                          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:4 }}>
                            {[["Fuel",fmtCurrency(cost.fuel_cost)],["Toll",fmtCurrency(cost.toll_cost)],["Driver",fmtCurrency(cost.driver_cost)],["Handling",fmtCurrency(cost.handling_cost)]].map(([l,v]) => (
                              <div key={l} style={{ display:"flex", justifyContent:"space-between", fontSize:10, color:COLORS.muted }}>
                                <span>{l}</span><span style={{ color:COLORS.text }}>{v}</span>
                              </div>
                            ))}
                          </div>
                          <div style={{ marginTop:8, paddingTop:8, borderTop:`1px solid ${COLORS.border}`, display:"flex", justifyContent:"space-between" }}>
                            <span style={{ fontSize:12, fontWeight:700, color:COLORS.text }}>Total</span>
                            <span style={{ fontSize:15, fontWeight:800, color, fontFamily:"'Syne',sans-serif" }}>{fmtCurrency(cost.total_cost)}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}

                  {/* SHAP */}
                  <div style={{ background:COLORS.card, borderRadius:10, padding:14, marginBottom:10, border:`1px solid ${COLORS.border2}` }}>
                    <div style={{ fontSize:9, color:COLORS.muted, letterSpacing:2.5, marginBottom:12, textTransform:"uppercase" }}>SHAP Risk Factors</div>
                    {result.shap_explanation?.map((s,i) => (
                      <div key={i} style={{ marginBottom:10 }}>
                        <div style={{ display:"flex", justifyContent:"space-between", marginBottom:4 }}>
                          <span style={{ fontSize:10, color:COLORS.muted }}>{s.feature}</span>
                          <span style={{ fontSize:10, fontWeight:700, color: s.impact>0 ? COLORS.high : COLORS.low, fontFamily:"'JetBrains Mono',monospace" }}>
                            {s.impact>0?"+":""}{s.impact?.toFixed(3)}
                          </span>
                        </div>
                        <div style={{ background:COLORS.dim, borderRadius:3, height:3, overflow:"hidden" }}>
                          <div style={{
                            width:`${Math.min(Math.abs(s.impact)*20,100)}%`, height:"100%", borderRadius:3,
                            background: s.impact>0 ? COLORS.high : COLORS.low,
                            boxShadow:`0 0 8px ${s.impact>0?COLORS.high:COLORS.low}60`
                          }}/>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Mitigation */}
                  <div style={{ fontSize:9, color:COLORS.muted, letterSpacing:2.5, marginBottom:10, textTransform:"uppercase" }}>Mitigation Options</div>
                  {result.mitigation?.map((m,i) => (
                    <div key={i} style={{
                      padding:"12px 14px", marginBottom:8, background:COLORS.card,
                      borderRadius:8, border:`1px solid ${COLORS.border2}`,
                      borderLeft:`2px solid ${[COLORS.primary,COLORS.medium,COLORS.muted][i]||COLORS.muted}`
                    }}>
                      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start" }}>
                        <div>
                          <div style={{ fontSize:11, color:COLORS.text, fontWeight:600, marginBottom:3 }}>{m.option}</div>
                          <div style={{ fontSize:10, color:COLORS.muted }}>{m.detail}</div>
                        </div>
                        <div style={{ textAlign:"right" }}>
                          <div style={{ fontSize:11, color:COLORS.primary, fontWeight:700 }}>{m.cost_impact}</div>
                          <div style={{ fontSize:9, color:COLORS.muted }}>{m.time_impact}</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Analyze Map — zooms in after analyze */}
          <div style={{ flex:1, position:"relative" }}>
            <MapContainer center={[16,78]} zoom={6} style={{ height:"100%", width:"100%" }} zoomControl={false}>
              <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" attribution=""/>

              {/* Background dotted highway corridors */}
              {highways.map(hw => (
                HIGHWAY_COORDS[hw.highway] && (
                  <Polyline key={hw.highway}
                    positions={HIGHWAY_COORDS[hw.highway]}
                    pathOptions={{ color:"#00b4d8", weight:1.5, opacity:0.4, dashArray:"6 5" }}
                  />
                )
              ))}

              {/* Selected route — solid bright line */}
              {result?.primary_route?.path && (() => {
                const coords = result.primary_route.path.map(c => CITY_COORDS[c]).filter(Boolean);
                return coords.length >= 2 ? (
                  <Polyline
                    positions={coords}
                    pathOptions={{ color:"#f72585", weight:5, opacity:0.95, lineCap:"round", lineJoin:"round" }}
                  />
                ) : null;
              })()}

              {/* Alternate route */}
              {result?.alternate_route?.path && (() => {
                const coords = result.alternate_route.path.map(c => CITY_COORDS[c]).filter(Boolean);
                return coords.length >= 2 ? (
                  <Polyline
                    positions={coords}
                    pathOptions={{ color:COLORS.medium, weight:3, opacity:0.7, dashArray:"10 5" }}
                  />
                ) : null;
              })()}

              {/* Route city markers */}
              {result?.primary_route?.path?.map((city,i) => {
                const coord = CITY_COORDS[city];
                if (!coord) return null;
                const isEndpoint = i===0 || i===result.primary_route.path.length-1;
                return (
                  <CircleMarker key={i} center={coord}
                    radius={isEndpoint ? 9 : 5}
                    pathOptions={{
                      color: isEndpoint ? "#f72585" : COLORS.primary,
                      fillColor: isEndpoint ? "#f72585" : COLORS.primary,
                      fillOpacity:0.9, weight:2
                    }}
                  >
                    <Tooltip permanent={isEndpoint}>
                      <div style={{ fontSize:11, fontWeight:700 }}>{city}</div>
                    </Tooltip>
                  </CircleMarker>
                );
              })}

              {/* Fly to route after analyze */}
              {routeCoords && <FlyToRoute coords={routeCoords} />}
            </MapContainer>

            {/* Segment panel */}
            <div style={{
              position:"absolute", top:16, right:16, zIndex:999,
              background:`${COLORS.bg}f0`, borderRadius:12,
              padding:"14px 16px", border:`1px solid ${COLORS.border2}`,
              backdropFilter:"blur(12px)", maxWidth:250, maxHeight:"70vh", overflow:"auto"
            }}>
              <div style={{ fontSize:9, color:COLORS.muted, letterSpacing:2.5, marginBottom:12, textTransform:"uppercase" }}>Segment Analysis</div>
              {result?.primary_route?.seg_details?.map((seg,i) => (
                <div key={i} className="seg-row" style={{ padding:"8px 0", borderBottom:`1px solid ${COLORS.border}`, transition:"background 0.1s" }}>
                  <div style={{ fontSize:10, color:COLORS.text }}>{seg.from} → {seg.to}</div>
                  <div style={{ display:"flex", justifyContent:"space-between", marginTop:3 }}>
                    <span style={{ fontSize:9, color:COLORS.muted }}>{seg.highway} · {seg.distance_km}km</span>
                    <span style={{ fontSize:10, color:RL(seg.seg_risk >= 60 ? "HIGH" : seg.seg_risk >= 35 ? "MEDIUM" : "LOW"), fontWeight:700, fontFamily:"'JetBrains Mono',monospace" }}>
                      {seg.seg_risk?.toFixed(1)}
                    </span>
                  </div>
                </div>
              )) || (
                <div style={{ fontSize:10, color:COLORS.muted }}>Run analysis to see segment breakdown</div>
              )}
            </div>

            {/* Route legend */}
            {result && (
              <div style={{
                position:"absolute", bottom:20, left:20, zIndex:999,
                background:`${COLORS.bg}f0`, borderRadius:12,
                padding:"14px 18px", border:`1px solid ${COLORS.border2}`,
                backdropFilter:"blur(12px)", animation:"fadeIn 0.5s ease"
              }}>
                <div style={{ fontSize:9, color:COLORS.muted, letterSpacing:2.5, marginBottom:10, textTransform:"uppercase" }}>Route Map</div>
                {[
                  { color:"#f72585", dash:false, label:"Primary Route" },
                  { color:COLORS.medium, dash:true, label:"Alternate Route" },
                  { color:COLORS.primary, dash:true, label:"Highway Corridors" },
                ].map(r => (
                  <div key={r.label} style={{ display:"flex", alignItems:"center", gap:8, marginBottom:5 }}>
                    <div style={{ width:24, height:r.dash?0:3, background:r.dash?"transparent":r.color, borderRadius:2, boxShadow:r.dash?"none":`0 0 6px ${r.color}80`,
                      borderTop:r.dash?`2px dashed ${r.color}`:"none" }}/>
                    <span style={{ fontSize:10, color:COLORS.muted }}>{r.label}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ======== ANALYTICS TAB ======== */}
      {tab === "analytics" && (
        <div style={{ padding:28, overflow:"auto", height:"calc(100vh - 60px)" }}>
          <div style={{ maxWidth:1280, margin:"0 auto" }}>
            <div style={{ marginBottom:28 }}>
              <h1 style={{ fontSize:28, fontWeight:800, color:COLORS.text, marginBottom:4, fontFamily:"'Syne',sans-serif" }}>
                Analytics <span style={{ color:COLORS.primary }}>Dashboard</span>
              </h1>
              <p style={{ fontSize:13, color:COLORS.muted }}>Real-time highway risk intelligence · {highways.length} corridors monitored</p>
            </div>

            {/* Top Stats */}
            <div style={{ display:"flex", gap:14, marginBottom:24 }}>
              <StatCard label="Total Highways" value={highways.length} sub="Monitored corridors" color={COLORS.primary} icon="⬡"/>
              <StatCard label="High Risk" value={highRisk} sub="Avoid immediately" color={COLORS.high} icon="⚠"/>
              <StatCard label="Average Risk" value={`${avgRisk}`} sub="All corridors" color={COLORS.medium} icon="◉"/>
              <StatCard label="Segments" value={segments.length} sub="City-to-city" color={COLORS.low} icon="◈"/>
              <StatCard label="Cities" value="35+" sub="South India" color="#c77dff" icon="⊕"/>
            </div>

            {/* Charts row */}
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:16, marginBottom:20 }}>
              {/* Pie: Highway risk distribution */}
              <div style={{ background:COLORS.card, borderRadius:16, padding:20, border:`1px solid ${COLORS.border2}` }}>
                <div style={{ fontSize:10, color:COLORS.muted, letterSpacing:2.5, marginBottom:16, textTransform:"uppercase" }}>Highway Risk Distribution</div>
                <div style={{ width:"100%", height:200 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={riskPieData} cx="50%" cy="50%" innerRadius={55} outerRadius={80}
                        dataKey="value" stroke="none" paddingAngle={3}>
                        {riskPieData.map((d,i) => (
                          <Cell key={i} fill={d.color} style={{ filter:`drop-shadow(0 0 8px ${d.color}60)` }}/>
                        ))}
                      </Pie>
                      <ReTooltip contentStyle={{ background:COLORS.card, border:`1px solid ${COLORS.border2}`, borderRadius:8, color:COLORS.text }}/>
                      <Legend iconType="circle" iconSize={8} formatter={(v) => <span style={{ color:COLORS.muted, fontSize:11 }}>{v}</span>}/>
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Pie: Segment risk */}
              <div style={{ background:COLORS.card, borderRadius:16, padding:20, border:`1px solid ${COLORS.border2}` }}>
                <div style={{ fontSize:10, color:COLORS.muted, letterSpacing:2.5, marginBottom:16, textTransform:"uppercase" }}>Segment Risk Breakdown</div>
                <div style={{ width:"100%", height:200 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={segPieData} cx="50%" cy="50%" outerRadius={80}
                        dataKey="value" stroke="none" paddingAngle={2} label={({ name, percent }) => `${name} ${(percent*100).toFixed(0)}%`}
                        labelLine={false}>
                        {segPieData.map((d,i) => <Cell key={i} fill={d.color}/>)}
                      </Pie>
                      <ReTooltip contentStyle={{ background:COLORS.card, border:`1px solid ${COLORS.border2}`, borderRadius:8, color:COLORS.text }}/>
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Bar: Model accuracy */}
              <div style={{ background:COLORS.card, borderRadius:16, padding:20, border:`1px solid ${COLORS.border2}` }}>
                <div style={{ fontSize:10, color:COLORS.muted, letterSpacing:2.5, marginBottom:16, textTransform:"uppercase" }}>Model Performance</div>
                <div style={{ width:"100%", height:200 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={[
                      { name:"XGBoost", acc:78, f1:82, auc:86 },
                      { name:"LightGBM", acc:78.5, f1:83, auc:87 },
                      { name:"RandomForest", acc:77.9, f1:81, auc:85 },
                    ]} margin={{ top:5, right:10, left:-20, bottom:5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke={COLORS.dim}/>
                      <XAxis dataKey="name" tick={{ fontSize:10, fill:COLORS.muted }}/>
                      <YAxis tick={{ fontSize:10, fill:COLORS.muted }} domain={[70,90]}/>
                      <ReTooltip contentStyle={{ background:COLORS.card, border:`1px solid ${COLORS.border2}`, borderRadius:8, color:COLORS.text }}/>
                      <Bar dataKey="acc" fill={COLORS.primary} name="Accuracy" radius={[4,4,0,0]}/>
                      <Bar dataKey="f1" fill={COLORS.low} name="F1 Score" radius={[4,4,0,0]}/>
                      <Bar dataKey="auc" fill="#c77dff" name="AUC-ROC" radius={[4,4,0,0]}/>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* Highway risk bars + Segment Radar */}
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16, marginBottom:20 }}>
              <div style={{ background:COLORS.card, borderRadius:16, padding:20, border:`1px solid ${COLORS.border2}` }}>
                <div style={{ fontSize:10, color:COLORS.muted, letterSpacing:2.5, marginBottom:18, textTransform:"uppercase" }}>Highway Risk Scores</div>
                {highways.map((hw,i) => (
                  <div key={hw.highway} style={{ marginBottom:12 }}>
                    <div style={{ display:"flex", justifyContent:"space-between", marginBottom:5 }}>
                      <span style={{ fontSize:12, color:COLORS.text, fontWeight:600 }}>{hw.highway}</span>
                      <div style={{ display:"flex", gap:8, alignItems:"center" }}>
                        <span style={{ fontSize:12, color:RL(hw.risk_level), fontFamily:"'JetBrains Mono',monospace", fontWeight:700 }}>
                          {(hw.risk_score||0).toFixed(1)}
                        </span>
                        <RiskBadge level={hw.risk_level}/>
                      </div>
                    </div>
                    <ProgressBar value={hw.risk_score||0} color={RL(hw.risk_level)} height={5}/>
                  </div>
                ))}
              </div>

              {/* Radar of risk dimensions */}
              <div style={{ background:COLORS.card, borderRadius:16, padding:20, border:`1px solid ${COLORS.border2}` }}>
                <div style={{ fontSize:10, color:COLORS.muted, letterSpacing:2.5, marginBottom:16, textTransform:"uppercase" }}>Risk Dimension Radar</div>
                <div style={{ width:"100%", height:240 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart data={[
                      { factor:"Weather", score: highways.length ? (highways.reduce((a,h)=>(a+(h.risk_score||0)*0.3),0)/highways.length) : 40 },
                      { factor:"Traffic", score: highways.length ? (highways.reduce((a,h)=>(a+(h.risk_score||0)*0.25),0)/highways.length) : 35 },
                      { factor:"News Risk", score: highways.length ? (highways.reduce((a,h)=>(a+(h.risk_score||0)*0.2),0)/highways.length) : 30 },
                      { factor:"Congestion", score: highways.length ? (highways.reduce((a,h)=>(a+(h.risk_score||0)*0.15),0)/highways.length) : 25 },
                      { factor:"Rain Risk", score: highways.length ? (highways.reduce((a,h)=>(a+(h.risk_score||0)*0.1),0)/highways.length) : 20 },
                    ]}>
                      <PolarGrid stroke={COLORS.dim}/>
                      <PolarAngleAxis dataKey="factor" tick={{ fontSize:11, fill:COLORS.muted }}/>
                      <Radar dataKey="score" stroke={COLORS.primary} fill={COLORS.primary} fillOpacity={0.2}/>
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* Segment Table */}
            <div style={{ background:COLORS.card, borderRadius:16, padding:20, border:`1px solid ${COLORS.border2}`, marginBottom:20 }}>
              <div style={{ fontSize:10, color:COLORS.muted, letterSpacing:2.5, marginBottom:16, textTransform:"uppercase" }}>Segment-Level Risk Breakdown ({segments.length} segments)</div>
              <div style={{ overflowX:"auto" }}>
                <table style={{ width:"100%", borderCollapse:"collapse", fontSize:11 }}>
                  <thead>
                    <tr style={{ borderBottom:`1px solid ${COLORS.border2}` }}>
                      {["Segment","Highway","Distance","Risk Score","Level","Status"].map(h => (
                        <th key={h} style={{ padding:"10px 14px", textAlign:"left", color:COLORS.muted, fontWeight:600, letterSpacing:0.8, fontSize:10, textTransform:"uppercase" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {segments.map((seg,i) => (
                      <tr key={i} className="seg-row" style={{ borderBottom:`1px solid ${COLORS.border}`, transition:"background 0.15s" }}>
                        <td style={{ padding:"10px 14px", color:COLORS.text, fontWeight:500 }}>{seg.segment}</td>
                        <td style={{ padding:"10px 14px", color:COLORS.muted }}>{seg.highway}</td>
                        <td style={{ padding:"10px 14px", color:COLORS.muted, fontFamily:"'JetBrains Mono',monospace" }}>{seg.distance_km}km</td>
                        <td style={{ padding:"10px 14px" }}>
                          <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                            <div style={{ width:44, background:COLORS.dim, borderRadius:3, height:4 }}>
                              <div style={{ width:`${Math.min(seg.risk_score||0,100)}%`, background:RL(seg.risk_level), height:4, borderRadius:3, boxShadow:`0 0 6px ${RL(seg.risk_level)}60` }}/>
                            </div>
                            <span style={{ color:RL(seg.risk_level), fontWeight:700, fontFamily:"'JetBrains Mono',monospace" }}>{(seg.risk_score||0).toFixed(1)}</span>
                          </div>
                        </td>
                        <td style={{ padding:"10px 14px" }}><RiskBadge level={seg.risk_level}/></td>
                        <td style={{ padding:"10px 14px", color:COLORS.muted, fontSize:10 }}>
                          {seg.risk_level==="HIGH" ? "⛔ Avoid segment" : seg.risk_level==="MEDIUM" ? "⚠ Monitor closely" : "✓ Safe to transit"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Tech Stack */}
            <div style={{ background:COLORS.card, borderRadius:16, padding:20, border:`1px solid ${COLORS.border2}` }}>
              <div style={{ fontSize:10, color:COLORS.muted, letterSpacing:2.5, marginBottom:16, textTransform:"uppercase" }}>Technology Stack</div>
              <div style={{ display:"flex", flexWrap:"wrap", gap:8 }}>
                {[
                  ["Apache Kafka",COLORS.low,"Event Streaming"],
                  ["Apache Spark",COLORS.medium,"Batch Processing"],
                  ["Apache Airflow",COLORS.primary,"Orchestration"],
                  ["XGBoost","#8b5cf6","ML Model"],
                  ["LightGBM","#ec4899","ML Model"],
                  ["RandomForest","#14b8a6","ML Model"],
                  ["SHAP","#f97316","Explainability"],
                  ["LangGraph",COLORS.primary,"AI Agent"],
                  ["Groq LLM",COLORS.low,"Inference"],
                  ["FastAPI",COLORS.high,"Backend"],
                  ["Dijkstra",COLORS.medium,"Routing"],
                  ["ORS API","#8b5cf6","Distances"],
                  ["MLflow","#3b82f6","MLOps"],
                  ["React + Leaflet",COLORS.primary,"Frontend"],
                ].map(([name,color,cat]) => (
                  <div key={name} style={{
                    background:`${color}12`, border:`1px solid ${color}30`,
                    borderRadius:8, padding:"7px 14px", display:"flex", alignItems:"center", gap:7,
                    transition:"transform 0.15s"
                  }}
                  onMouseEnter={e=>e.currentTarget.style.transform="scale(1.04)"}
                  onMouseLeave={e=>e.currentTarget.style.transform=""}>
                    <div style={{ width:7, height:7, borderRadius:"50%", background:color, boxShadow:`0 0 6px ${color}` }}/>
                    <span style={{ fontSize:11, color:COLORS.text, fontWeight:600 }}>{name}</span>
                    <span style={{ fontSize:9, color:COLORS.muted }}>{cat}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ======== PIPELINE TAB ======== */}
      {tab === "pipeline" && (
        <div style={{ padding:28, overflow:"auto", height:"calc(100vh - 60px)" }}>
          <div style={{ maxWidth:960, margin:"0 auto" }}>
            <div style={{ marginBottom:28 }}>
              <h1 style={{ fontSize:28, fontWeight:800, color:COLORS.text, marginBottom:4, fontFamily:"'Syne',sans-serif" }}>
                Data <span style={{ color:COLORS.primary }}>Pipeline</span>
              </h1>
              <p style={{ fontSize:13, color:COLORS.muted }}>End-to-end MLOps pipeline architecture</p>
            </div>

            {[
              { step:"01", title:"Data Ingestion", color:COLORS.low,
                tools:["OpenWeatherMap API","TomTom Traffic API","NewsData.io API"],
                desc:"Live weather, traffic, and news data fetched for 35 cities across 8 South India highways every 6 hours via Airflow-triggered producer.",
                output:"35 JSON events → Kafka topic highway-events" },
              { step:"02", title:"Event Streaming", color:COLORS.primary,
                tools:["Apache Kafka (KRaft)","Kafka Producer","Kafka Consumer"],
                desc:"KRaft mode Kafka (no Zookeeper) handles the event stream. Producer pushes city weather events, consumer reads and persists to SQLite.",
                output:"SQLite highway_events table (88+ rows)" },
              { step:"03", title:"Batch Processing", color:COLORS.medium,
                tools:["Apache Spark local[2]","PySpark DataFrame API","Feature Engineering"],
                desc:"Spark reads highway events, computes rain_risk, event_risk, congestion_risk, news_risk with weighted scoring across 4 dimensions.",
                output:"Aggregated per-highway feature vectors" },
              { step:"04", title:"ML Prediction", color:"#8b5cf6",
                tools:["XGBoost (50%)","LightGBM (30%)","RandomForest (20%)"],
                desc:"Ensemble of 3 models trained on 24,000 records (20k real NHAI + 4k synthetic). Weighted average produces final disruption probability.",
                output:"Risk scores + confidence intervals per highway" },
              { step:"05", title:"Route Intelligence", color:"#ec4899",
                tools:["Dijkstra Algorithm","ORS API","Segment Scoring"],
                desc:"Risk-weighted Dijkstra finds safest path across 35-city graph. Segment-level scoring (36 segments) enables precise rerouting. ORS provides real road distances.",
                output:"Primary + alternate routes with toll cost breakdown" },
              { step:"06", title:"AI Agent", color:"#14b8a6",
                tools:["LangGraph","Groq LLaMA-3.3","FastAPI MCP"],
                desc:"LangGraph multi-step agent: fetches live highway data → detects cities in query → calls Dijkstra → sends context to Groq LLM for natural language response.",
                output:"Plain English freight advisory" },
              { step:"07", title:"MLOps Loop", color:"#f97316",
                tools:["MLflow Tracking","Feedback DAG","Auto-retrain"],
                desc:"User delay reports stored in feedback table. Airflow retrain_dag checks weekly — if 5+ new records, merges with training data and retrains all 3 models.",
                output:"Updated models.pkl + MLflow experiment log" },
            ].map((p,i) => (
              <div key={i} style={{ display:"flex", gap:18, marginBottom:18, animation:`fadeUp 0.3s ease ${i*0.06}s both` }}>
                <div style={{ display:"flex", flexDirection:"column", alignItems:"center" }}>
                  <div style={{
                    width:48, height:48, borderRadius:12,
                    background:`${p.color}18`, border:`1px solid ${p.color}40`,
                    display:"flex", alignItems:"center", justifyContent:"center",
                    fontSize:13, fontWeight:800, color:p.color, flexShrink:0,
                    fontFamily:"'JetBrains Mono',monospace",
                    boxShadow:`0 0 20px ${p.color}20`
                  }}>{p.step}</div>
                  {i < 6 && <div style={{ width:2, flex:1, background:`linear-gradient(${p.color}50, transparent)`, marginTop:6 }}/>}
                </div>
                <div style={{
                  flex:1, background:COLORS.card, borderRadius:14, padding:20,
                  border:`1px solid ${p.color}20`, marginBottom:4,
                  borderLeft:`3px solid ${p.color}`,
                  transition:"transform 0.2s, box-shadow 0.2s"
                }}
                onMouseEnter={e=>{e.currentTarget.style.transform="translateX(4px)";e.currentTarget.style.boxShadow=`0 8px 30px ${p.color}15`}}
                onMouseLeave={e=>{e.currentTarget.style.transform="";e.currentTarget.style.boxShadow=""}}>
                  <div style={{ fontSize:15, fontWeight:700, color:COLORS.text, marginBottom:10, fontFamily:"'Syne',sans-serif" }}>{p.title}</div>
                  <div style={{ display:"flex", flexWrap:"wrap", gap:6, marginBottom:12 }}>
                    {p.tools.map(t => (
                      <span key={t} style={{
                        fontSize:10, background:`${p.color}15`, color:p.color,
                        padding:"3px 10px", borderRadius:6, border:`1px solid ${p.color}30`, fontWeight:600
                      }}>{t}</span>
                    ))}
                  </div>
                  <div style={{ fontSize:12, color:COLORS.muted, lineHeight:1.8, marginBottom:10 }}>{p.desc}</div>
                  <div style={{ fontSize:11, color:COLORS.dim+99, borderTop:`1px solid ${COLORS.border}`, paddingTop:10, fontFamily:"'JetBrains Mono',monospace", fontSize:10 }}>
                    <span style={{ color:p.color }}>→ </span><span style={{ color:COLORS.muted }}>{p.output}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ======== FLOATING CHATBOT ======== */}
      <div style={{ position:"fixed", bottom:28, right:28, zIndex:2000 }}>
        {!chatOpen && (
          <div style={{ display:"flex", flexDirection:"column", alignItems:"center", gap:8 }}>
            {/* "ASK ME" label */}
            <div style={{
              background:`linear-gradient(135deg, ${COLORS.primary}, #0077b6)`,
              color:"white", fontSize:10, fontWeight:800, letterSpacing:2,
              padding:"5px 14px", borderRadius:20,
              boxShadow:`0 4px 20px ${COLORS.primary}50`,
              fontFamily:"'Syne',sans-serif",
              animation:"float 3s ease-in-out infinite",
              whiteSpace:"nowrap"
            }}>
              ASK ME ✦
            </div>
            <button onClick={() => {
              setChatOpen(true);
              if (chatMsgs.length === 0) setChatMsgs([{
                role:"bot",
                text:"Hey! I'm your freight intelligence assistant. Ask me about highway risk, route safety, or disruptions across South India. 🚛"
              }]);
            }} style={{
              width:62, height:62, borderRadius:"50%",
              background:`linear-gradient(135deg, ${COLORS.primary}, #0077b6)`,
              border:"none", cursor:"pointer", fontSize:24,
              display:"flex", alignItems:"center", justifyContent:"center",
              boxShadow:`0 6px 30px ${COLORS.primary}60`,
              animation:"float 3s ease-in-out infinite",
              position:"relative", transition:"transform 0.2s"
            }}
            onMouseEnter={e=>e.currentTarget.style.transform="scale(1.1)"}
            onMouseLeave={e=>e.currentTarget.style.transform=""}>
              🚛
              <div style={{
                position:"absolute", top:-2, right:-2,
                width:16, height:16, borderRadius:"50%",
                background: pulse ? COLORS.low : COLORS.medium,
                border:`2px solid ${COLORS.bg}`,
                transition:"background 0.5s"
              }}/>
            </button>
          </div>
        )}

        {chatOpen && (
          <div style={{
            width:400, height:540, background:COLORS.surface,
            border:`1px solid ${COLORS.border2}`, borderRadius:20,
            display:"flex", flexDirection:"column",
            boxShadow:`0 30px 80px rgba(0,0,0,0.9)`,
            animation:"fadeUp 0.25s ease"
          }}>
            {/* Chat Header */}
            <div style={{
              padding:"16px 18px", borderBottom:`1px solid ${COLORS.border2}`,
              background:`linear-gradient(135deg, ${COLORS.card}, ${COLORS.primary}12)`,
              borderRadius:"20px 20px 0 0",
              display:"flex", alignItems:"center", justifyContent:"space-between"
            }}>
              <div style={{ display:"flex", alignItems:"center", gap:12 }}>
                <div style={{
                  width:42, height:42, borderRadius:12,
                  background:`linear-gradient(135deg, ${COLORS.primary}, #0077b6)`,
                  display:"flex", alignItems:"center", justifyContent:"center", fontSize:20,
                  boxShadow:`0 0 20px ${COLORS.primary}40`
                }}>🚛</div>
                <div>
                  <div style={{ fontSize:14, fontWeight:700, color:COLORS.text, fontFamily:"'Syne',sans-serif" }}>Freight Assistant</div>
                  <div style={{ fontSize:10, color:COLORS.low, display:"flex", alignItems:"center", gap:5 }}>
                    <div style={{ width:6, height:6, borderRadius:"50%", background:COLORS.low, boxShadow:`0 0 6px ${COLORS.low}` }}/>
                    Groq + LangGraph · Online
                  </div>
                </div>
              </div>
              <button onClick={() => setChatOpen(false)} style={{
                background:`${COLORS.dim}40`, border:`1px solid ${COLORS.border2}`, borderRadius:8,
                color:COLORS.muted, cursor:"pointer", fontSize:14, lineHeight:1,
                padding:"6px 10px", transition:"all 0.15s"
              }}
              onMouseEnter={e=>{e.currentTarget.style.background=COLORS.dim;e.currentTarget.style.color=COLORS.text}}
              onMouseLeave={e=>{e.currentTarget.style.background=`${COLORS.dim}40`;e.currentTarget.style.color=COLORS.muted}}>✕</button>
            </div>

            {/* Messages */}
            <div style={{ flex:1, overflow:"auto", padding:14, display:"flex", flexDirection:"column", gap:10 }}>
              {chatMsgs.map((m,i) => (
                <div key={i} style={{ display:"flex", justifyContent: m.role==="user" ? "flex-end" : "flex-start", animation:"fadeUp 0.2s ease" }}>
                  {m.role === "bot" && (
                    <div style={{ width:28, height:28, borderRadius:8, background:`${COLORS.primary}20`, border:`1px solid ${COLORS.primary}30`, display:"flex", alignItems:"center", justifyContent:"center", fontSize:13, marginRight:8, flexShrink:0, alignSelf:"flex-end" }}>🚛</div>
                  )}
                  <div style={{
                    maxWidth:"78%", padding:"10px 14px", fontSize:12, lineHeight:1.7,
                    borderRadius: m.role==="user" ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
                    background: m.role==="user"
                      ? `linear-gradient(135deg, ${COLORS.primary}, #0077b6)`
                      : COLORS.card,
                    color: m.role==="user" ? "white" : COLORS.text,
                    border: m.role==="bot" ? `1px solid ${COLORS.border2}` : "none",
                    boxShadow: m.role==="user" ? `0 4px 15px ${COLORS.primary}30` : "none"
                  }}>{m.text}</div>
                </div>
              ))}
              {chatLoading && (
                <div style={{ display:"flex", gap:5, padding:"8px 12px", background:COLORS.card, borderRadius:12, width:"fit-content", border:`1px solid ${COLORS.border2}` }}>
                  {[0,1,2].map(i => (
                    <div key={i} style={{ width:7, height:7, borderRadius:"50%", background:COLORS.primary, animation:`dot 1s ease ${i*0.2}s infinite` }}/>
                  ))}
                </div>
              )}
              <div ref={chatEnd}/>
            </div>

            {/* Quick Questions */}
            {chatMsgs.length <= 1 && (
              <div style={{ padding:"0 14px 10px", display:"flex", flexWrap:"wrap", gap:5 }}>
                {["What is my source & destination?","Is NH-44 safe today?","Best route Hyderabad→Chennai","Monsoon disruptions?"].map(q => (
                  <button key={q} className="quick-q" onClick={() => setChatInput(q)} style={{
                    background:COLORS.card, border:`1px solid ${COLORS.border2}`, borderRadius:8,
                    padding:"5px 10px", color:COLORS.muted, cursor:"pointer",
                    fontSize:10, fontFamily:"'Space Grotesk',sans-serif", transition:"all 0.15s"
                  }}>{q}</button>
                ))}
              </div>
            )}

            {/* Input */}
            <div style={{ padding:"12px 14px", borderTop:`1px solid ${COLORS.border2}`, display:"flex", gap:8 }}>
              <input value={chatInput} onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => e.key==="Enter" && handleChat()}
                placeholder="Ask about highways, routes, risk..."
                style={{
                  flex:1, background:COLORS.card, border:`1px solid ${COLORS.border2}`,
                  borderRadius:10, padding:"10px 14px", color:COLORS.text,
                  fontSize:12, outline:"none", fontFamily:"'Space Grotesk',sans-serif",
                  transition:"border-color 0.2s"
                }}
                onFocus={e=>e.target.style.borderColor=COLORS.primary}
                onBlur={e=>e.target.style.borderColor=COLORS.border2}
              />
              <button onClick={handleChat} disabled={chatLoading} style={{
                background:`linear-gradient(135deg, ${COLORS.primary}, #0077b6)`,
                border:"none", borderRadius:10, padding:"10px 16px",
                cursor:"pointer", fontSize:16, color:"white",
                boxShadow:`0 4px 15px ${COLORS.primary}40`,
                transition:"transform 0.15s"
              }}
              onMouseEnter={e=>e.currentTarget.style.transform="scale(1.05)"}
              onMouseLeave={e=>e.currentTarget.style.transform=""}>→</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
