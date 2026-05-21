import { useState, useMemo, useCallback } from "react";
import {
  AreaChart, Area, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from "recharts";
 
// ─────────────────────────────────────────────────────────────────────────────
// 1. DESIGN TOKENS
// ─────────────────────────────────────────────────────────────────────────────
 
const T = {
  bg:       "#080d1a",
  surface:  "#0d1526",
  surface2: "#111f35",
  surface3: "#162440",
  border:   "#1e3054",
  borderHi: "#2a4270",
  gold:     "#c9a84c",
  goldFaint:"rgba(201,168,76,0.12)",
  green:    "#10b981",
  greenFaint:"rgba(16,185,129,0.12)",
  yellow:   "#f59e0b",
  yellowFaint:"rgba(245,158,11,0.12)",
  red:      "#ef4444",
  redFaint: "rgba(239,68,68,0.12)",
  blue:     "#3b82f6",
  cyan:     "#06b6d4",
  text:     "#e8eef7",
  textMuted:"#8ba3c7",
  textDim:  "#3d5a87",
  mono:     "'Space Mono', 'Courier New', monospace",
  serif:    "'DM Serif Display', Georgia, serif",
  sans:     "'DM Sans', system-ui, sans-serif",
};
 
// ─────────────────────────────────────────────────────────────────────────────
// 2. CALC ENGINE — alle KPIs als pure functions
// ─────────────────────────────────────────────────────────────────────────────
 
const r0 = v => Math.round(v);
const r1 = v => Math.round(v * 10) / 10;
const r2 = v => Math.round(v * 100) / 100;
 
function fmtEUR(v) {
  if (!isFinite(v)) return "—";
  const a = Math.abs(v);
  if (a >= 1_000_000) return `${(v / 1_000_000).toFixed(2).replace(".", ",")} Mio. €`;
  return new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(v);
}
function fmtPct(v, dec = 2) {
  if (!isFinite(v)) return "—";
  return `${v.toFixed(dec).replace(".", ",")} %`;
}
function fmtX(v) {
  if (!isFinite(v) || v > 99) return "> 99x";
  return `${v.toFixed(1).replace(".", ",")}x`;
}
function fmtYr(v) {
  if (!isFinite(v) || v > 99) return "< 0 / n.v.";
  return `${v.toFixed(1).replace(".", ",")} J.`;
}
 
/**
 * Instandhaltungsrücklage (IHR) nach Gebäudealter.
 * Basis: % des Kaufpreises als pragmatische Näherung.
 * HINWEIS: Methodisch korrekt wäre €/m²/Jahr auf Herstellungswert
 * (Peters-Formel: HK × 1,5 / GND). In Teuerlagen (München, HH)
 * überschätzt diese Methode die IHR, da KP >> HK. Nutzer sollten
 * in solchen Märkten die Bewirtschaftungskosten-Quote entsprechend anpassen.
 */
function calcIHR(kaufpreis, baujahr) {
  const age = 2025 - baujahr;
  if (age < 10)  return kaufpreis * 0.003;   // Neubau/KfW: minimal
  if (age < 25)  return kaufpreis * 0.006;   // Junger Bestand: gelegentliche Reparaturen
  if (age < 40)  return kaufpreis * 0.010;   // Mittlerer Bestand: zyklische Erneuerungen
  return kaufpreis * 0.013;                  // Altbau: laufend hoher Bedarf
}
 
/** IRR via Newton-Raphson (konvergiert für typische Immobilien-Cashflows) */
function calcIRR(initialInvestment, cashflows) {
  // initialInvestment = negativer EK-Einsatz
  let rate = 0.08;
  for (let i = 0; i < 300; i++) {
    let f = initialInvestment, df = 0;
    cashflows.forEach((c, t) => {
      const p = Math.pow(1 + rate, t + 1);
      f += c / p;
      df -= (t + 1) * c / (p * (1 + rate));
    });
    if (Math.abs(df) < 1e-12) break;
    const rn = rate - f / df;
    if (Math.abs(rn - rate) < 1e-6) return rn * 100;
    rate = Math.min(Math.max(rn, -0.999), 50);
  }
  return rate * 100;
}
 
/** NPV mit konstantem Diskontierungssatz */
function calcNPV(initialInvestment, cashflows, rate) {
  return cashflows.reduce(
    (s, c, t) => s + c / Math.pow(1 + rate, t + 1),
    initialInvestment
  );
}
 
/**
 * Master-Berechnung: alle KPIs aus einem Inputs-Objekt.
 * Gibt ein flaches Ergebnis-Objekt zurück.
 */
function calcAll(inp) {
  const {
    kaufpreis, knk, jahresmiete, bew,
    ek, zins, tilgung,
    steuer, gebaeude,
    isDenkmal, dkSan, dkAfa, regAfa,
    baujahr, wertZuwachs, mietSteigerung,
    leerstand, diskont,
  } = inp;
 
  // ── Transaktion ─────────────────────────────────────────────────────────
  const grunderwerbsteuer  = kaufpreis * 0.035;
  const notarGrundbuch     = kaufpreis * 0.020;
  const makler             = Math.max(0, kaufpreis * ((knk - 5.5) / 100));
  const knkAbs             = kaufpreis * (knk / 100);
  const gesamt             = kaufpreis + knkAbs;
 
  // ── Erträge ──────────────────────────────────────────────────────────────
  const bewKosten    = jahresmiete * (bew / 100);
  const leerstandAbs = jahresmiete * (leerstand / 100);
  const ihr          = calcIHR(kaufpreis, baujahr);
  // FIX (Bug 6): Einheitliche Basis — IHR in BEIDEN Größen enthalten.
  // NOI (für Cap Rate): vor Finanzierung, inkl. IHR, ohne Leerstand (Marktstandard)
  // nettoMiete (für DSCR/CF/Rendite): inkl. IHR + Leerstand (konservativ, bankenkonform)
  const noi        = jahresmiete - bewKosten - ihr;
  const nettoMiete = jahresmiete - bewKosten - leerstandAbs - ihr;
 
  // ── Renditen ─────────────────────────────────────────────────────────────
  const brutto    = kaufpreis > 0 ? r2((jahresmiete / kaufpreis) * 100) : 0;
  const faktor    = jahresmiete > 0 ? r1(kaufpreis / jahresmiete) : 0;
  const nettoRend = gesamt    > 0 ? r2((nettoMiete / gesamt)  * 100) : 0;
  const capRate   = kaufpreis > 0 ? r2((noi       / kaufpreis) * 100) : 0;
 
  // ── Finanzierung ─────────────────────────────────────────────────────────
  const ekAbs    = gesamt * (ek / 100);
  const fk       = gesamt - ekAbs;
  const zinslast = fk * (zins / 100);
  const tilgAbs  = fk * (tilgung / 100);
  const kd       = zinslast + tilgAbs;  // Kapitaldienst
  // FIX (Bug 1): LTV = FK / Kaufpreis (Marktwert), NICHT / Gesamtinvestition.
  // Die Bank bewertet das Pfand (die Immobilie), nicht die Transaktionskosten des Käufers.
  // KNK sind nach Kauf sofort wertlos als Sicherheit → Bank sieht nur den Kaufpreis.
  const ltv      = r1(kaufpreis > 0 ? (fk / kaufpreis) * 100 : 0);
  const dscr     = r2(kd > 0 ? nettoMiete / kd : 99);
 
  // ── AfA (Steuerliche Abschreibung) ───────────────────────────────────────
  const afaBasis = gesamt * (gebaeude / 100);
  let afa;
  if (isDenkmal) {
    const san = afaBasis * (dkSan / 100);
    afa = (afaBasis - san) * 0.02 + san * (dkAfa / 100);
  } else {
    afa = afaBasis * (regAfa / 100);
  }
 
  // ── Steuer & Cashflow ────────────────────────────────────────────────────
  const stlErgebnis  = nettoMiete - zinslast - afa;
  const steuerlast   = stlErgebnis * (steuer / 100);
  const cfPreM       = r2((nettoMiete - kd) / 12);
  const cfPostM      = r2((nettoMiete - kd - steuerlast) / 12);
 
  // ── Return-Metriken ───────────────────────────────────────────────────────
  const gewinnNachZinsen = nettoMiete - zinslast;
  const roe              = r2(ekAbs > 0 ? (gewinnNachZinsen / ekAbs) * 100 : 0);
  const roi              = r2(gesamt > 0 ? (nettoMiete / gesamt) * 100 : 0);
 
  // ── Operative Kennzahlen ─────────────────────────────────────────────────
  // FIX (Bug 3): Break-Even-Miete muss bew% UND leerstand% berücksichtigen.
  // Formel: BEMiete × (1 - bew% - leerstand%) = kd
  // → BEMiete = kd / (1 - bew% - leerstand%)
  const kostensatz = (bew + leerstand) / 100;
  const beMonat = r2((kostensatz < 1 && kd > 0)
    ? (kd / (1 - kostensatz)) / 12
    : 0);
  const amort   = cfPostM * 12 > 0 ? r1(ekAbs / (cfPostM * 12)) : null;
 
  // ── 10-Jahres-Projektion ─────────────────────────────────────────────────
  // FIX (Bug 4): Korrektes Annuitätendarlehen-Modell.
  // Die Annuität (= Zins + Tilgung) bleibt KONSTANT. Bei sinkendem Zinsanteil
  // steigt der Tilgungsanteil — das ist das klassische deutsche Annuitätendarlehen.
  // Annuität p.a. ≈ FK × (zins% + tilgung%) / 100
  // Jedes Jahr: Zinsen = Restschuld × Zinssatz; Tilgung = Annuität - Zinsen
  const annuitaet = fk * (zins + tilgung) / 100;  // fixe Jahresrate
 
  const proj = [];
  let debt    = fk;
  let mBrutto = jahresmiete;
  let iwert   = kaufpreis;
  const irrCFs = [];
  let cumCfPost = 0;  // für MOIC-Fix
 
  for (let y = 1; y <= 10; y++) {
    const mBew    = mBrutto * (bew / 100);
    const mLeer   = mBrutto * (leerstand / 100);
    const mIhr    = calcIHR(kaufpreis, baujahr);  // IHR bleibt konstant (nicht mietindexiert)
    const mNetto  = mBrutto - mBew - mLeer - mIhr;
 
    // Annuität: Zinsen auf Restschuld, Tilgung = Annuität − Zinsen
    const yZins   = debt * (zins / 100);
    const yTilg   = Math.min(debt, Math.max(0, annuitaet - yZins));
    const yKd     = yZins + yTilg;
 
    const yStl    = (mNetto - yZins - afa) * (steuer / 100);
    const yCfPre  = mNetto - yKd;
    const yCfPost = yCfPre - yStl;
 
    cumCfPost += yCfPost;  // kumuliert für MOIC
    debt   = Math.max(0, debt - yTilg);
    iwert *= (1 + wertZuwachs / 100);
    const eq = iwert - debt;
    // IRR-CF: laufender Post-Tax-CF + im Jahr 10 realisierter Equity-Gewinn
    irrCFs.push(yCfPost + (y === 10 ? Math.max(0, eq - ekAbs) : 0));
    proj.push({
      y: `J${y}`,
      cfPre:    r0(yCfPre / 12), cfPost: r0(yCfPost / 12),
      equity:   r0(eq), iwert: r0(iwert), schulden: r0(debt),
    });
    mBrutto *= (1 + mietSteigerung / 100);
  }
 
  let irrVal = 0;
  try { irrVal = r2(calcIRR(-ekAbs, irrCFs)); } catch {}
  const npvVal  = r0(calcNPV(-ekAbs, irrCFs, diskont / 100));
 
  // FIX (Bug 2): MOIC = (kumulierte Cashflows + Terminal Equity) / initiales EK.
  // Nur die finale Equity zu nehmen ignoriert alle laufenden Cashflow-Returns.
  const finalEq = proj[9]?.equity ?? ekAbs;
  const moic    = r2(ekAbs > 0 ? (cumCfPost + finalEq) / ekAbs : 0);
 
  // ── Kostenstruktur (Donut-Chart) ─────────────────────────────────────────
  const pie = [
    { name: "Kaufpreis",         value: kaufpreis,      color: "#3b82f6" },
    { name: "Grunderwerbsteuer", value: grunderwerbsteuer, color: "#c9a84c" },
    { name: "Notar/Grundbuch",   value: notarGrundbuch, color: "#8b5cf6" },
    { name: "Makler",            value: makler,         color: "#06b6d4" },
  ].filter(d => d.value > 0);
 
  return {
    // Transaktion
    knkAbs, grunderwerbsteuer, notarGrundbuch, makler, gesamt,
    // Erträge
    bewKosten, leerstandAbs, ihr, noi, nettoMiete,
    // Renditen
    brutto, faktor, nettoRend, capRate,
    // Finanzierung
    ekAbs, fk, zinslast, tilgAbs, kd, annuitaet, ltv, dscr,
    // Steuer
    afa, steuerlast, stlErgebnis,
    // Cashflow
    cfPreM, cfPostM,
    // Returns
    roe, roi,
    // Operativ
    beMonat, amort,
    // Erweitert
    irrVal, npvVal, moic,
    // Zeitreihen
    proj, pie,
  };
}
 
/** Szenario-Varianten */
function calcScenario(base, mode) {
  if (mode === "optimistic") return calcAll({
    ...base,
    jahresmiete: base.jahresmiete * 1.10,
    zins: Math.max(0.5, base.zins - 0.5),
    leerstand: Math.max(0, base.leerstand - 1),
    wertZuwachs: base.wertZuwachs + 1.5,
  });
  if (mode === "pessimistic") return calcAll({
    ...base,
    jahresmiete: base.jahresmiete * 0.90,
    zins: base.zins + 0.8,
    leerstand: base.leerstand + 3,
    wertZuwachs: Math.max(0, base.wertZuwachs - 1.5),
    bew: Math.min(35, base.bew + 3),
  });
  return calcAll(base);
}
 
// ─────────────────────────────────────────────────────────────────────────────
// 3. AMPEL-LOGIK
// ─────────────────────────────────────────────────────────────────────────────
 
function getAmpel(key, val) {
  const rules = {
    brutto:    v => v >= 6 ? "green" : v >= 4    ? "yellow" : "red",
    nettoRend: v => v >= 4.5 ? "green" : v >= 3  ? "yellow" : "red",
    capRate:   v => v >= 5 ? "green" : v >= 3.5  ? "yellow" : "red",
    faktor:    v => v <= 20 ? "green" : v <= 25  ? "yellow" : "red",
    dscr:      v => v >= 1.3 ? "green" : v >= 1.1 ? "yellow" : "red",
    ltv:       v => v <= 70 ? "green" : v <= 80  ? "yellow" : "red",
    cfPreM:    v => v >= 0 ? "green" : v >= -150  ? "yellow" : "red",
    cfPostM:   v => v >= 0 ? "green" : v >= -150  ? "yellow" : "red",
    roe:       v => v >= 8 ? "green" : v >= 5    ? "yellow" : "red",
    irrVal:    v => v >= 8 ? "green" : v >= 5    ? "yellow" : "red",
    npvVal:    v => v >= 0 ? "green"              : "red",
    moic:      v => v >= 2 ? "green" : v >= 1.5  ? "yellow" : "red",
  };
  const fn = rules[key];
  return fn ? fn(val) : "yellow";
}
 
const AMP = {
  green:  { color: T.green,  bg: T.greenFaint,  label: "Gut",       border: "rgba(16,185,129,0.25)" },
  yellow: { color: T.yellow, bg: T.yellowFaint, label: "Akzeptabel",border: "rgba(245,158,11,0.25)" },
  red:    { color: T.red,    bg: T.redFaint,    label: "Kritisch",  border: "rgba(239,68,68,0.25)" },
};
 
// ─────────────────────────────────────────────────────────────────────────────
// 4. DEFAULT-STATE
// ─────────────────────────────────────────────────────────────────────────────
 
const DEFAULT = {
  kaufpreis: 450000, knk: 8.5, jahresmiete: 16800, bew: 18,
  ek: 25, zins: 3.8, tilgung: 2.0,
  steuer: 42, gebaeude: 80,
  isDenkmal: false, dkSan: 60, dkAfa: 9.0, regAfa: 2.0,
  baujahr: 1975, wertZuwachs: 2.0, mietSteigerung: 1.5,
  leerstand: 3, diskont: 5.0,
};
 
// ─────────────────────────────────────────────────────────────────────────────
// 5. STILISIERTE PRIMITIVE
// ─────────────────────────────────────────────────────────────────────────────
 
// Beschrifteter Slider
function SliderRow({ label, value, min, max, step = 1, unit = "", onChange, tooltip }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 5 }}>
        <label style={{ fontSize: 12, color: T.textMuted, fontFamily: T.sans, letterSpacing: "0.04em", textTransform: "uppercase" }}>
          {label}
          {tooltip && <span title={tooltip} style={{ cursor: "help", marginLeft: 4, color: T.textDim }}>ⓘ</span>}
        </label>
        <span style={{ fontFamily: T.mono, fontSize: 13, color: T.gold, fontWeight: 700 }}>
          {typeof value === "number"
            ? value % 1 === 0 ? value.toLocaleString("de-DE") : value.toFixed(step < 0.5 ? 1 : 0).replace(".", ",")
            : value}
          {unit && <span style={{ fontSize: 11, color: T.textDim, marginLeft: 2 }}>{unit}</span>}
        </span>
      </div>
      <input
        type="range" min={min} max={max} step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        style={{
          width: "100%", height: 3, appearance: "none", background: `linear-gradient(to right, ${T.gold} ${((value - min) / (max - min)) * 100}%, ${T.border} 0%)`,
          borderRadius: 4, cursor: "pointer", outline: "none",
        }}
      />
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 2 }}>
        <span style={{ fontSize: 10, color: T.textDim }}>{min}{unit}</span>
        <span style={{ fontSize: 10, color: T.textDim }}>{max}{unit}</span>
      </div>
    </div>
  );
}
 
// Zahleneingabe
function NumInput({ label, value, step = 1000, unit = "€", onChange, tooltip }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={{ display: "block", fontSize: 12, color: T.textMuted, fontFamily: T.sans, letterSpacing: "0.04em", textTransform: "uppercase", marginBottom: 5 }}>
        {label}
        {tooltip && <span title={tooltip} style={{ cursor: "help", marginLeft: 4, color: T.textDim }}>ⓘ</span>}
      </label>
      <div style={{ position: "relative" }}>
        <input
          type="number" value={value} step={step}
          onChange={e => onChange(Number(e.target.value))}
          style={{
            width: "100%", background: T.surface3, border: `1px solid ${T.border}`, borderRadius: 6,
            color: T.text, fontFamily: T.mono, fontSize: 14, padding: "8px 36px 8px 10px",
            outline: "none", boxSizing: "border-box",
          }}
        />
        <span style={{ position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)", fontSize: 12, color: T.textDim }}>{unit}</span>
      </div>
    </div>
  );
}
 
// Abschnittskopf
function SectionHead({ label }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "22px 0 14px" }}>
      <div style={{ height: 1, flex: 1, background: T.border }} />
      <span style={{ fontFamily: T.sans, fontSize: 11, color: T.textDim, letterSpacing: "0.1em", textTransform: "uppercase", whiteSpace: "nowrap" }}>{label}</span>
      <div style={{ height: 1, flex: 1, background: T.border }} />
    </div>
  );
}
 
// KPI-Karte mit Ampel
function KpiCard({ label, value, subLabel, ampelKey, ampelVal, expert }) {
  const ampelColor = ampelKey ? AMP[getAmpel(ampelKey, ampelVal ?? (typeof value === "number" ? value : 0))] : null;
  return (
    <div style={{
      background: T.surface2,
      border: `1px solid ${ampelColor ? ampelColor.border : T.border}`,
      borderRadius: 10,
      padding: "14px 16px",
      position: "relative",
      overflow: "hidden",
    }}>
      {ampelColor && (
        <div style={{
          position: "absolute", top: 0, left: 0, right: 0, height: 2,
          background: ampelColor.color,
        }} />
      )}
      <div style={{ fontSize: 11, color: T.textMuted, fontFamily: T.sans, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>
        {label}
      </div>
      <div style={{ fontFamily: T.mono, fontSize: 20, fontWeight: 700, color: ampelColor ? ampelColor.color : T.text, lineHeight: 1.1 }}>
        {value}
      </div>
      {subLabel && (
        <div style={{ fontSize: 11, color: T.textDim, marginTop: 4, fontFamily: T.sans }}>
          {subLabel}
        </div>
      )}
      {ampelColor && (
        <div style={{
          position: "absolute", top: 10, right: 10,
          fontSize: 10, fontFamily: T.sans, fontWeight: 600,
          color: ampelColor.color, background: ampelColor.bg,
          borderRadius: 4, padding: "2px 6px",
        }}>
          {ampelColor.label}
        </div>
      )}
    </div>
  );
}
 
// Benchmark-Box
function BenchmarkBox({ text }) {
  return (
    <div style={{
      background: T.goldFaint,
      border: `1px solid rgba(201,168,76,0.25)`,
      borderRadius: 8, padding: "10px 14px", marginTop: 10,
    }}>
      <span style={{ fontFamily: T.sans, fontSize: 12, color: T.textMuted, lineHeight: 1.5 }}>💡 {text}</span>
    </div>
  );
}
 
// Chart-Tooltip
function ChartTooltip({ active, payload, label, formatFn }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: T.surface3, border: `1px solid ${T.border}`, borderRadius: 8, padding: "10px 14px", fontFamily: T.sans, fontSize: 12 }}>
      <div style={{ color: T.textMuted, marginBottom: 6, fontWeight: 600 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color, marginBottom: 2 }}>
          {p.name}: <strong>{formatFn ? formatFn(p.value) : p.value}</strong>
        </div>
      ))}
    </div>
  );
}
 
// Toggle-Switch
function Toggle({ label, checked, onChange }) {
  return (
    <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer", marginBottom: 12 }}>
      <div style={{
        width: 38, height: 20, borderRadius: 10, background: checked ? T.gold : T.border,
        position: "relative", transition: "background 0.2s", flexShrink: 0,
      }}>
        <div style={{
          width: 16, height: 16, borderRadius: "50%", background: T.text,
          position: "absolute", top: 2, left: checked ? 20 : 2, transition: "left 0.2s",
        }} />
      </div>
      <span style={{ fontFamily: T.sans, fontSize: 13, color: T.textMuted }}>{label}</span>
    </label>
  );
}
 
// ─────────────────────────────────────────────────────────────────────────────
// 6. HAUPT-APP
// ─────────────────────────────────────────────────────────────────────────────
 
export default function YieldBase() {
  // State
  const [inp, setInp] = useState(DEFAULT);
  const [tab, setTab] = useState("eingabe");    // eingabe | dashboard | analyse | bericht
  const [mode, setMode] = useState("expert");  // einsteiger | expert
 
  // Updater
  const set = useCallback((key, val) => setInp(prev => ({ ...prev, [key]: val })), []);
 
  // Berechnungen (memoized)
  const res = useMemo(() => calcAll(inp), [inp]);
  const scOpt = useMemo(() => calcScenario(inp, "optimistic"), [inp]);
  const scReal = useMemo(() => res, [res]);
  const scPess = useMemo(() => calcScenario(inp, "pessimistic"), [inp]);
 
  const isExpert = mode === "expert";
 
  // Styling helpers
  const tabStyle = (t) => ({
    padding: "10px 20px",
    background: tab === t ? T.surface3 : "transparent",
    border: tab === t ? `1px solid ${T.border}` : "1px solid transparent",
    borderRadius: 8,
    color: tab === t ? T.text : T.textMuted,
    cursor: "pointer",
    fontFamily: T.sans,
    fontSize: 13,
    fontWeight: tab === t ? 600 : 400,
    transition: "all 0.15s",
  });
 
  return (
    <div style={{ background: T.bg, minHeight: "100vh", color: T.text, fontFamily: T.sans }}>
 
      {/* Google Fonts */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Space+Mono:wght@400;700&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300&display=swap');
        input[type=range]::-webkit-slider-thumb { -webkit-appearance:none; width:14px; height:14px; border-radius:50%; background:${T.gold}; cursor:pointer; margin-top:-5px; }
        input[type=range]::-webkit-slider-runnable-track { height:3px; border-radius:4px; }
        input[type=number] { -moz-appearance: textfield; }
        input[type=number]::-webkit-inner-spin-button { display: none; }
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 4px; } ::-webkit-scrollbar-track { background: ${T.surface}; } ::-webkit-scrollbar-thumb { background: ${T.border}; border-radius: 4px; }
      `}</style>
 
      {/* ── HEADER ──────────────────────────────────────────────────────────── */}
      <header style={{
        background: T.surface,
        borderBottom: `1px solid ${T.border}`,
        padding: "0 32px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        height: 64,
        position: "sticky", top: 0, zIndex: 100,
      }}>
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <svg width="32" height="32" viewBox="0 0 100 100">
            <defs>
              <linearGradient id="g" x1="0%" y1="100%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#4f46e5" />
                <stop offset="100%" stopColor="#06b6d4" />
              </linearGradient>
            </defs>
            <path d="M50 15 L80 32 L50 50 L20 32Z" fill="url(#g)" />
            <path d="M20 32 L50 50 L50 85 L35 77 L35 58 L20 50Z" fill="#0f172a" />
            <path d="M80 32 L50 50 L50 85 L65 77 L65 58 L80 50Z" fill="url(#g)" opacity="0.8" />
          </svg>
          <div>
            <div style={{ fontFamily: T.serif, fontSize: 20, color: T.text, lineHeight: 1 }}>YieldBase</div>
            <div style={{ fontFamily: T.sans, fontSize: 11, color: T.textDim, letterSpacing: "0.08em", marginTop: 1 }}>INVESTMENT ANALYTICS v2</div>
          </div>
        </div>
 
        {/* Tabs */}
        <nav style={{ display: "flex", gap: 6 }}>
          {[["eingabe","⌨ Eingabe"],["dashboard","▦ KPI Dashboard"],["analyse","⛶ Analyse"],["bericht","▤ Bericht"]].map(([t, lbl]) => (
            <button key={t} style={tabStyle(t)} onClick={() => setTab(t)}>{lbl}</button>
          ))}
        </nav>
 
        {/* Mode Toggle */}
        <div style={{ display: "flex", gap: 4, background: T.surface2, border: `1px solid ${T.border}`, borderRadius: 8, padding: 4 }}>
          {[["einsteiger","Einsteiger"],["expert","Experte"]].map(([m, lbl]) => (
            <button key={m} onClick={() => setMode(m)} style={{
              padding: "5px 14px", borderRadius: 6,
              background: mode === m ? T.gold : "transparent",
              color: mode === m ? T.bg : T.textMuted,
              border: "none", cursor: "pointer", fontFamily: T.sans, fontSize: 12, fontWeight: 600,
              transition: "all 0.15s",
            }}>{lbl}</button>
          ))}
        </div>
      </header>
 
      {/* ── MAIN ─────────────────────────────────────────────────────────────── */}
      <main style={{ maxWidth: 1400, margin: "0 auto", padding: "28px 24px" }}>
 
        {/* Quick-Status-Bar (immer sichtbar) */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
          gap: 10, marginBottom: 24,
          background: T.surface,
          border: `1px solid ${T.border}`,
          borderRadius: 10, padding: "14px 20px",
        }}>
          {[
            ["Gesamtinvestition", fmtEUR(res.gesamt)],
            ["Brutto-Rendite",    fmtPct(res.brutto)],
            ["Netto-Rendite",     fmtPct(res.nettoRend)],
            ["Cashflow/Mon.",     fmtEUR(res.cfPreM)],
            ["DSCR",              res.dscr.toString().replace(".", ",")],
            ["EK-Rendite (ROE)",  fmtPct(res.roe)],
          ].map(([lbl, val], i) => (
            <div key={i} style={{ textAlign: "center" }}>
              <div style={{ fontSize: 11, color: T.textDim, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 4 }}>{lbl}</div>
              <div style={{ fontFamily: T.mono, fontSize: 15, fontWeight: 700, color: T.gold }}>{val}</div>
            </div>
          ))}
        </div>
 
        {/* ═══════════════════════════════════════════════════════ TAB: EINGABE */}
        {tab === "eingabe" && (
          <div style={{ display: "grid", gridTemplateColumns: "380px 1fr", gap: 20 }}>
 
            {/* ── Linke Spalte: Inputs ── */}
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
 
              {/* Panel: Objekt */}
              <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: "18px 20px" }}>
                <h2 style={{ fontFamily: T.serif, fontSize: 17, color: T.text, margin: "0 0 16px", display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ color: T.gold }}>01</span> Objekt & Transaktion
                </h2>
                <NumInput label="Kaufpreis" value={inp.kaufpreis} step={5000} onChange={v => set("kaufpreis", v)}
                  tooltip="Brutto-Verkaufspreis ohne Nebenkosten." />
                <SliderRow label="Kaufnebenkosten (KNK)" value={inp.knk} min={5} max={15} step={0.5} unit=" %"
                  onChange={v => set("knk", v)}
                  tooltip="Grunderwerbsteuer (3,5–6,5 %) + Notar (≈2 %) + Makler (0–3,57 %)" />
                <NumInput label="Jahres-Kaltmiete" value={inp.jahresmiete} step={500} onChange={v => set("jahresmiete", v)}
                  tooltip="Aktuelle Ist-Miete p.a. (netto, kalt)." />
                <SliderRow label="Bewirtschaftungskosten" value={inp.bew} min={5} max={35} step={1} unit=" %"
                  onChange={v => set("bew", v)}
                  tooltip="Verwaltung, nicht-umlagefähige Betriebskosten, Mietausfallwagnis. Standard: 15–22 %." />
                <SliderRow label="Leerstandsrisiko" value={inp.leerstand} min={0} max={15} step={0.5} unit=" %"
                  onChange={v => set("leerstand", v)}
                  tooltip="Erwarteter jährlicher Leerstand als %-Anteil der Jahresmiete." />
                <NumInput label="Baujahr" value={inp.baujahr} step={1} unit="J." onChange={v => set("baujahr", v)}
                  tooltip="Bestimmt automatisch die Instandhaltungsrücklage (jung: 0,4 % / mittel: 0,8 % / alt: 1,6 % p.a.)." />
                {!isExpert && (
                  <BenchmarkBox text={`Kaufpreisfaktor: ${fmtX(res.faktor)} — ${res.faktor <= 22 ? "Günstiger Einstieg (< 22x)." : res.faktor <= 27 ? "Marktüblich (22–27x)." : "Teuer (> 27x) – Rendite schwer darstellbar."}`} />
                )}
              </div>
 
              {/* Panel: Finanzierung */}
              <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: "18px 20px" }}>
                <h2 style={{ fontFamily: T.serif, fontSize: 17, color: T.text, margin: "0 0 16px", display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ color: T.gold }}>02</span> Finanzierung
                </h2>
                <SliderRow label="Eigenkapital-Quote" value={inp.ek} min={5} max={100} step={1} unit=" %"
                  onChange={v => set("ek", v)}
                  tooltip="Anteil der Gesamtinvestition aus Eigenmitteln." />
                <SliderRow label="Sollzins p.a." value={inp.zins} min={0.5} max={8} step={0.1} unit=" %"
                  onChange={v => set("zins", v)} />
                <SliderRow label="Anfangstilgung p.a." value={inp.tilgung} min={0.5} max={6} step={0.1} unit=" %"
                  onChange={v => set("tilgung", v)}
                  tooltip="Standard: 1,5–2 %. Höhere Tilgung = weniger Zinsrisiko, aber weniger Cashflow." />
                {!isExpert && (
                  <BenchmarkBox text={`DSCR ${res.dscr.toFixed(2).replace(".",",")} — ${res.dscr >= 1.3 ? "Bankfähig ✓" : res.dscr >= 1.1 ? "Akzeptabel (Grenzbereich)" : "Kritisch – Bank wird ablehnen"}`} />
                )}
              </div>
 
              {/* Panel: Steuer & AfA (nur Experte) */}
              {isExpert && (
                <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: "18px 20px" }}>
                  <h2 style={{ fontFamily: T.serif, fontSize: 17, color: T.text, margin: "0 0 16px", display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ color: T.gold }}>03</span> Steuer & AfA
                  </h2>
                  <SliderRow label="Persönlicher Steuersatz" value={inp.steuer} min={0} max={45} step={1} unit=" %"
                    onChange={v => set("steuer", v)} />
                  <SliderRow label="Gebäudeanteil" value={inp.gebaeude} min={40} max={100} step={1} unit=" %"
                    onChange={v => set("gebaeude", v)}
                    tooltip="Anteil am Gesamtkauf, der auf das Gebäude entfällt (Boden nicht abschreibbar)." />
                  <Toggle label="Denkmalschutz-AfA aktiv (§ 7i EStG)" checked={inp.isDenkmal} onChange={v => set("isDenkmal", v)} />
                  {inp.isDenkmal ? (
                    <>
                      <SliderRow label="Sanierungsanteil" value={inp.dkSan} min={10} max={90} step={1} unit=" %"
                        onChange={v => set("dkSan", v)} />
                      <SliderRow label="Denkmal-AfA-Satz" value={inp.dkAfa} min={3} max={12} step={0.5} unit=" %"
                        onChange={v => set("dkAfa", v)} />
                    </>
                  ) : (
                    <SliderRow label="Reguläre Gebäude-AfA" value={inp.regAfa} min={1} max={4} step={0.5} unit=" %"
                      onChange={v => set("regAfa", v)}
                      tooltip="Neubau ≥ 2023: 3 %. Altbau: 2 %. Denkmal: bis 9 % p.a. (§ 7i)." />
                  )}
                </div>
              )}
 
              {/* Panel: Szenario-Prämissen (nur Experte) */}
              {isExpert && (
                <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: "18px 20px" }}>
                  <h2 style={{ fontFamily: T.serif, fontSize: 17, color: T.text, margin: "0 0 16px", display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ color: T.gold }}>04</span> Projekt-Prämissen (10 J.)
                  </h2>
                  <SliderRow label="Wertzuwachs p.a." value={inp.wertZuwachs} min={-2} max={6} step={0.5} unit=" %"
                    onChange={v => set("wertZuwachs", v)} />
                  <SliderRow label="Mietsteigerung p.a." value={inp.mietSteigerung} min={0} max={5} step={0.25} unit=" %"
                    onChange={v => set("mietSteigerung", v)} />
                  <SliderRow label="Diskontierungssatz" value={inp.diskont} min={1} max={12} step={0.5} unit=" %"
                    onChange={v => set("diskont", v)}
                    tooltip="Wird für NPV-Berechnung verwendet. Richtwert: risikoadjustierter Kapitalkostensatz (5–8 %)." />
                </div>
              )}
            </div>
 
            {/* ── Rechte Spalte: Live-Ergebnis ── */}
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
 
              {/* Kernergebnis-Banner */}
              <div style={{
                background: `linear-gradient(135deg, ${T.surface2} 0%, ${T.surface3} 100%)`,
                border: `1px solid ${T.border}`,
                borderRadius: 12, padding: "22px 24px",
              }}>
                <div style={{ fontFamily: T.serif, fontSize: 14, color: T.textMuted, marginBottom: 6 }}>
                  Gesamtinvestition (inkl. {fmtPct(inp.knk)} KNK)
                </div>
                <div style={{ fontFamily: T.mono, fontSize: 34, fontWeight: 700, color: T.gold }}>
                  {fmtEUR(res.gesamt)}
                </div>
                <div style={{ display: "flex", gap: 20, marginTop: 14 }}>
                  {[
                    ["Eigenkapital", fmtEUR(res.ekAbs)],
                    ["Fremdkapital", fmtEUR(res.fk)],
                    ["Kaufnebenkosten", fmtEUR(res.knkAbs)],
                  ].map(([l, v]) => (
                    <div key={l}>
                      <div style={{ fontSize: 11, color: T.textDim, textTransform: "uppercase", letterSpacing: "0.05em" }}>{l}</div>
                      <div style={{ fontFamily: T.mono, fontSize: 14, color: T.text, marginTop: 2 }}>{v}</div>
                    </div>
                  ))}
                </div>
              </div>
 
              {/* KPI-Grid Einsteiger */}
              {!isExpert && (
                <>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                    <KpiCard label="Bruttorendite" value={fmtPct(res.brutto)} subLabel="Kaufpreis-Basis" ampelKey="brutto" ampelVal={res.brutto} />
                    <KpiCard label="Netto-Rendite" value={fmtPct(res.nettoRend)} subLabel="Gesamtinvestition" ampelKey="nettoRend" ampelVal={res.nettoRend} />
                    <KpiCard label="Kaufpreisfaktor" value={fmtX(res.faktor)} subLabel="Jahre bis Amortisation (brutto)" ampelKey="faktor" ampelVal={res.faktor} />
                    <KpiCard label="DSCR" value={res.dscr.toFixed(2).replace(".", ",")} subLabel="Schuldendeckungsgrad" ampelKey="dscr" ampelVal={res.dscr} />
                    <KpiCard label="Cashflow/Monat" value={fmtEUR(res.cfPreM)} subLabel="Vor Steuer" ampelKey="cfPreM" ampelVal={res.cfPreM} />
                    <KpiCard label="Break-Even-Miete" value={fmtEUR(res.beMonat)} subLabel="Mindestmiete/Monat" />
                  </div>
                  <BenchmarkBox text="Einsteiger-Benchmark: DSCR ≥ 1,15 für Bankfinanzierung. Netto-Rendite ≥ 4 % als Mindeststandard. Cashflow ≥ 0 € empfohlen." />
                </>
              )}
 
              {/* KPI-Grid Experte */}
              {isExpert && (
                <>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
                    <KpiCard label="Bruttorendite" value={fmtPct(res.brutto)} ampelKey="brutto" ampelVal={res.brutto} />
                    <KpiCard label="Netto-Rendite" value={fmtPct(res.nettoRend)} ampelKey="nettoRend" ampelVal={res.nettoRend} />
                    <KpiCard label="Cap Rate (NOI)" value={fmtPct(res.capRate)} ampelKey="capRate" ampelVal={res.capRate} />
                    <KpiCard label="Kaufpreisfaktor" value={fmtX(res.faktor)} ampelKey="faktor" ampelVal={res.faktor} />
                    <KpiCard label="DSCR" value={res.dscr.toFixed(2).replace(".",",")} ampelKey="dscr" ampelVal={res.dscr} />
                    <KpiCard label="LTV" value={fmtPct(res.ltv, 1)} ampelKey="ltv" ampelVal={res.ltv} />
                    <KpiCard label="CF pre-Tax / Mon." value={fmtEUR(res.cfPreM)} ampelKey="cfPreM" ampelVal={res.cfPreM} />
                    <KpiCard label="CF post-Tax / Mon." value={fmtEUR(res.cfPostM)} ampelKey="cfPostM" ampelVal={res.cfPostM} />
                    <KpiCard label="EK-Rendite (ROE)" value={fmtPct(res.roe)} ampelKey="roe" ampelVal={res.roe} />
                    <KpiCard label="IRR (10 J.)" value={fmtPct(res.irrVal)} ampelKey="irrVal" ampelVal={res.irrVal} />
                    <KpiCard label="NPV" value={fmtEUR(res.npvVal)} ampelKey="npvVal" ampelVal={res.npvVal} />
                    <KpiCard label="MOIC" value={fmtX(res.moic)} ampelKey="moic" ampelVal={res.moic} />
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
                    <KpiCard label="Break-Even-Miete" value={fmtEUR(res.beMonat)} subLabel="Mindestmiete / Monat" />
                    <KpiCard label="Amortisation EK" value={res.amort ? fmtYr(res.amort) : "Negativ"} subLabel="aus Post-Tax-CF" />
                    <KpiCard label="AfA p.a." value={fmtEUR(res.afa)} subLabel={inp.isDenkmal ? "Denkmal § 7i EStG" : "Regulär"} />
                  </div>
                </>
              )}
 
              {/* Kostenstruktur */}
              <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: "18px 20px" }}>
                <h3 style={{ fontFamily: T.serif, fontSize: 15, color: T.text, margin: "0 0 12px" }}>Kostenstruktur</h3>
                <div style={{ display: "flex", gap: 20, alignItems: "center" }}>
                  <div style={{ width: 110, height: 110, flexShrink: 0 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={res.pie} dataKey="value" innerRadius={30} outerRadius={52} paddingAngle={2} startAngle={90} endAngle={-270}>
                          {res.pie.map((d, i) => <Cell key={i} fill={d.color} />)}
                        </Pie>
                        <Tooltip formatter={v => fmtEUR(v)} contentStyle={{ background: T.surface3, border: `1px solid ${T.border}`, borderRadius: 6, fontSize: 12 }} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div style={{ flex: 1 }}>
                    {res.pie.map((d, i) => (
                      <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                        <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <span style={{ width: 8, height: 8, borderRadius: 2, background: d.color, flexShrink: 0 }} />
                          <span style={{ fontSize: 12, color: T.textMuted }}>{d.name}</span>
                        </span>
                        <span style={{ fontFamily: T.mono, fontSize: 12, color: T.text }}>{fmtEUR(d.value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
 
        {/* ═══════════════════════════════════════════ TAB: KPI DASHBOARD */}
        {tab === "dashboard" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
 
            <SectionHead label="Rendite & Ertrag" />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
              <KpiCard label="Bruttorendite" value={fmtPct(res.brutto)} subLabel="Jahresmiete / Kaufpreis" ampelKey="brutto" ampelVal={res.brutto} />
              <KpiCard label="Netto-Mietrendite" value={fmtPct(res.nettoRend)} subLabel="Nach Bewirtschaftung & Leerstand" ampelKey="nettoRend" ampelVal={res.nettoRend} />
              <KpiCard label="Cap Rate (NOI Yield)" value={fmtPct(res.capRate)} subLabel="Vor Finanzierung & Steuer" ampelKey="capRate" ampelVal={res.capRate} />
              <KpiCard label="Kaufpreisfaktor" value={fmtX(res.faktor)} subLabel="Brutto-Rückzahldauer" ampelKey="faktor" ampelVal={res.faktor} />
              <KpiCard label="Jahresmieteinnahmen" value={fmtEUR(inp.jahresmiete)} subLabel="Brutto" />
              <KpiCard label="Nettomietertrag p.a." value={fmtEUR(res.nettoMiete)} subLabel="Nach Bewirtschaftung+Leerstand" />
            </div>
 
            <SectionHead label="Cashflow & Liquidität" />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
              <KpiCard label="Cashflow / Monat (pre)" value={fmtEUR(res.cfPreM)} subLabel="Vor Steuer" ampelKey="cfPreM" ampelVal={res.cfPreM} />
              <KpiCard label="Cashflow / Monat (post)" value={fmtEUR(res.cfPostM)} subLabel="Nach Steuern & Steuerschild" ampelKey="cfPostM" ampelVal={res.cfPostM} />
              <KpiCard label="Cashflow / Jahr (pre)" value={fmtEUR(res.cfPreM * 12)} subLabel="Annualisiert" />
              <KpiCard label="Break-Even-Miete/Monat" value={fmtEUR(res.beMonat)} subLabel="Mindestmiete zum Kostendecken" />
              <KpiCard label="AfA (Steuerschild) p.a." value={fmtEUR(res.afa)} subLabel={inp.isDenkmal ? "§ 7i Denkmal-AfA" : `${inp.regAfa} % regulär`} />
              <KpiCard label="Steuerlast p.a." value={fmtEUR(res.steuerlast)} subLabel={`Steuersatz ${inp.steuer} %`} />
            </div>
 
            {isExpert && (
              <>
                <SectionHead label="Finanzierung & Verschuldung" />
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
                  <KpiCard label="DSCR" value={res.dscr.toFixed(2).replace(".",",")} subLabel="Schuldendeckungsgrad" ampelKey="dscr" ampelVal={res.dscr} />
                  <KpiCard label="LTV" value={fmtPct(res.ltv, 1)} subLabel="Loan-to-Value (FK/Gesamt)" ampelKey="ltv" ampelVal={res.ltv} />
                  <KpiCard label="Eigenkapital" value={fmtEUR(res.ekAbs)} subLabel={`${inp.ek} % der Gesamtinvestition`} />
                  <KpiCard label="Darlehen (FK)" value={fmtEUR(res.fk)} subLabel={`${(100-inp.ek)} % Fremdfinanzierung`} />
                  <KpiCard label="Zinslast p.a." value={fmtEUR(res.zinslast)} subLabel={`${inp.zins} % p.a. auf FK`} />
                  <KpiCard label="Kapitaldienst p.a." value={fmtEUR(res.kd)} subLabel="Zins + Tilgung" />
                </div>
 
                <SectionHead label="Investment-Returns (10-Jahres-Horizont)" />
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
                  <KpiCard label="ROE (EK-Rendite)" value={fmtPct(res.roe)} subLabel="Leveraged Return" ampelKey="roe" ampelVal={res.roe} />
                  <KpiCard label="ROI" value={fmtPct(res.roi)} subLabel="Gesamtkapitalrendite" />
                  <KpiCard label="IRR (10 Jahre)" value={fmtPct(res.irrVal)} subLabel="Interner Zinsfuß (inkl. Wertzuwachs)" ampelKey="irrVal" ampelVal={res.irrVal} />
                  <KpiCard label="NPV" value={fmtEUR(res.npvVal)} subLabel={`Bei ${inp.diskont} % Diskont`} ampelKey="npvVal" ampelVal={res.npvVal} />
                  <KpiCard label="MOIC" value={fmtX(res.moic)} subLabel="Multiple on Invested Capital" ampelKey="moic" ampelVal={res.moic} />
                  <KpiCard label="EK-Amortisation" value={res.amort ? fmtYr(res.amort) : "n.v."} subLabel="Jahre bis EK-Rückfluss" />
                </div>
 
                <SectionHead label="Risiko & Substanz" />
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
                  <KpiCard label="Instandhaltung p.a." value={fmtEUR(res.ihr)} subLabel={`Baujahr ${inp.baujahr} — auto`} />
                  <KpiCard label="Leerstandsverlust p.a." value={fmtEUR(res.leerstandAbs)} subLabel={`${inp.leerstand} % Leerstand`} />
                  <KpiCard label="NOI (Nettobetriebsertrag)" value={fmtEUR(res.noi)} subLabel="Nach IHR, vor Finanzierung" />
                  <KpiCard label="KNK absolut" value={fmtEUR(res.knkAbs)} subLabel={`${inp.knk} % des Kaufpreises`} />
                  <KpiCard label="Grunderwerbsteuer" value={fmtEUR(res.grunderwerbsteuer)} subLabel="3,5 % (variiert je Bundesland)" />
                  <KpiCard label="Notar/Grundbuch" value={fmtEUR(res.notarGrundbuch)} subLabel="≈ 2 % des Kaufpreises" />
                </div>
              </>
            )}
          </div>
        )}
 
        {/* ═══════════════════════════════════════════ TAB: ANALYSE */}
        {tab === "analyse" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
 
            {/* Cashflow-Verlauf */}
            <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: "20px 24px" }}>
              <h3 style={{ fontFamily: T.serif, fontSize: 17, color: T.text, margin: "0 0 4px" }}>Cashflow-Projektion (10 Jahre)</h3>
              <p style={{ fontSize: 12, color: T.textDim, margin: "0 0 16px" }}>Monatlicher Cashflow vor und nach Steuer — realistisches Basisszenario</p>
              <div style={{ display: "flex", gap: 16, marginBottom: 12 }}>
                {[
                  { color: T.cyan,  label: "CF pre-Tax / Monat" },
                  { color: T.gold,  label: "CF post-Tax / Monat" },
                ].map(({ color, label }) => (
                  <span key={label} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: T.textMuted }}>
                    <span style={{ width: 10, height: 10, borderRadius: 2, background: color }} /> {label}
                  </span>
                ))}
              </div>
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart data={res.proj} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
                  <defs>
                    <linearGradient id="gradCyan" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={T.cyan} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={T.cyan} stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="gradGold" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={T.gold} stopOpacity={0.25} />
                      <stop offset="95%" stopColor={T.gold} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={T.border} vertical={false} />
                  <XAxis dataKey="y" tick={{ fill: T.textDim, fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: T.textDim, fontSize: 11 }} axisLine={false} tickLine={false}
                    tickFormatter={v => v >= 0 ? `${v} €` : `${v} €`} />
                  <Tooltip content={<ChartTooltip formatFn={v => `${v} €`} />} />
                  <Area type="monotone" dataKey="cfPre" name="CF pre-Tax" stroke={T.cyan} fill="url(#gradCyan)" strokeWidth={2} dot={false} />
                  <Area type="monotone" dataKey="cfPost" name="CF post-Tax" stroke={T.gold} fill="url(#gradGold)" strokeWidth={2} dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
 
            {/* Vermögensaufbau */}
            <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: "20px 24px" }}>
              <h3 style={{ fontFamily: T.serif, fontSize: 17, color: T.text, margin: "0 0 4px" }}>Vermögensaufbau (Equity Buildup)</h3>
              <p style={{ fontSize: 12, color: T.textDim, margin: "0 0 16px" }}>Eigenkapital-Entwicklung = Immobilienwert − Restschuld</p>
              <div style={{ display: "flex", gap: 16, marginBottom: 12 }}>
                {[
                  { color: T.green,  label: "Eigenkapital (Equity)" },
                  { color: T.blue,   label: "Immobilienwert" },
                  { color: T.red,    label: "Restschuld" },
                ].map(({ color, label }) => (
                  <span key={label} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: T.textMuted }}>
                    <span style={{ width: 10, height: 10, borderRadius: 2, background: color }} /> {label}
                  </span>
                ))}
              </div>
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={res.proj} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={T.border} vertical={false} />
                  <XAxis dataKey="y" tick={{ fill: T.textDim, fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: T.textDim, fontSize: 11 }} axisLine={false} tickLine={false}
                    tickFormatter={v => Math.abs(v) >= 1000 ? `${Math.round(v/1000)}k` : v} />
                  <Tooltip content={<ChartTooltip formatFn={v => fmtEUR(v)} />} />
                  <Line type="monotone" dataKey="equity" name="Eigenkapital" stroke={T.green} strokeWidth={2.5} dot={false} />
                  <Line type="monotone" dataKey="iwert" name="Immobilienwert" stroke={T.blue} strokeWidth={2} dot={false} strokeDasharray="6 3" />
                  <Line type="monotone" dataKey="schulden" name="Restschuld" stroke={T.red} strokeWidth={1.5} dot={false} strokeDasharray="3 3" />
                </LineChart>
              </ResponsiveContainer>
            </div>
 
            {/* Szenario-Vergleich */}
            <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: "20px 24px" }}>
              <h3 style={{ fontFamily: T.serif, fontSize: 17, color: T.text, margin: "0 0 4px" }}>Szenario-Vergleich</h3>
              <p style={{ fontSize: 12, color: T.textDim, margin: "0 0 20px" }}>
                Optimistisch (+10 % Miete, −0,5 % Zins, +1,5 % Wert, −1 % Leerstand) vs. Pessimistisch (−10 % Miete, +0,8 % Zins, ...)
              </p>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: T.sans, fontSize: 13 }}>
                  <thead>
                    <tr>
                      {[["KPI",""],["Optimistisch","#10b981"],["Realistisch","#c9a84c"],["Pessimistisch","#ef4444"]].map(([h, c]) => (
                        <th key={h} style={{ textAlign: h === "KPI" ? "left" : "right", padding: "8px 14px", color: c || T.textMuted, fontSize: 12, fontWeight: 600, borderBottom: `1px solid ${T.border}`, letterSpacing: "0.04em" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      ["Bruttorendite",     r => fmtPct(r.brutto),    "brutto"],
                      ["Netto-Rendite",     r => fmtPct(r.nettoRend), "nettoRend"],
                      ["DSCR",              r => r.dscr.toFixed(2).replace(".",","), "dscr"],
                      ["Cashflow / Monat",  r => fmtEUR(r.cfPreM),    "cfPreM"],
                      ["ROE",               r => fmtPct(r.roe),        "roe"],
                      ["IRR (10 J.)",       r => fmtPct(r.irrVal),     "irrVal"],
                      ["NPV",               r => fmtEUR(r.npvVal),     "npvVal"],
                      ["MOIC",              r => fmtX(r.moic),          "moic"],
                    ].map(([label, fmt, aKey], ri) => (
                      <tr key={label} style={{ background: ri % 2 === 0 ? "transparent" : T.surface2 }}>
                        <td style={{ padding: "10px 14px", color: T.textMuted }}>{label}</td>
                        {[scOpt, scReal, scPess].map((sc, si) => {
                          const val = fmt(sc);
                          const numVal = sc[aKey];
                          const ampel = aKey ? AMP[getAmpel(aKey, numVal)] : null;
                          return (
                            <td key={si} style={{ padding: "10px 14px", textAlign: "right", fontFamily: T.mono, color: ampel ? ampel.color : T.text }}>
                              {val}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
 
        {/* ═══════════════════════════════════════════ TAB: BERICHT */}
        {tab === "bericht" && (
          <div style={{ maxWidth: 900, margin: "0 auto" }}>
 
            {/* Executive Summary Box */}
            <div style={{
              background: `linear-gradient(135deg, ${T.surface2} 0%, ${T.surface3} 100%)`,
              border: `1px solid ${T.borderHi}`,
              borderRadius: 14, padding: "30px 36px", marginBottom: 20,
            }}>
              <div style={{ fontFamily: T.serif, fontSize: 28, color: T.text, marginBottom: 6 }}>Investment Summary</div>
              <div style={{ fontFamily: T.sans, fontSize: 13, color: T.textDim, marginBottom: 24 }}>YieldBase Analytics · Stand: {new Date().toLocaleDateString("de-DE")}</div>
 
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 20, marginBottom: 24 }}>
                {[
                  { label: "Gesamtinvestition", value: fmtEUR(res.gesamt) },
                  { label: "Jahresmiete (Brutto)", value: fmtEUR(inp.jahresmiete) },
                  { label: "Eigenkapital", value: fmtEUR(res.ekAbs) },
                ].map(({ label, value }) => (
                  <div key={label} style={{ background: "rgba(0,0,0,0.2)", borderRadius: 8, padding: "14px 16px" }}>
                    <div style={{ fontSize: 11, color: T.textDim, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>{label}</div>
                    <div style={{ fontFamily: T.mono, fontSize: 20, fontWeight: 700, color: T.gold }}>{value}</div>
                  </div>
                ))}
              </div>
 
              <div style={{ height: 1, background: T.border, margin: "20px 0" }} />
 
              {/* Gesamt-Rating */}
              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 12, color: T.textDim, marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.06em" }}>KPI-Gesamtbewertung</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {[
                    ["Rendite", res.nettoRend, "nettoRend"],
                    ["Cashflow", res.cfPreM, "cfPreM"],
                    ["DSCR", res.dscr, "dscr"],
                    ["LTV", res.ltv, "ltv"],
                    ["ROE", res.roe, "roe"],
                    ["IRR", res.irrVal, "irrVal"],
                    ["NPV", res.npvVal, "npvVal"],
                  ].map(([lbl, val, key]) => {
                    const a = AMP[getAmpel(key, val)];
                    return (
                      <span key={lbl} style={{ fontFamily: T.sans, fontSize: 12, padding: "4px 10px", borderRadius: 6, background: a.bg, color: a.color, border: `1px solid ${a.border}` }}>
                        {lbl}
                      </span>
                    );
                  })}
                </div>
              </div>
 
              {/* Narrative */}
              <div style={{ fontFamily: T.sans, fontSize: 13, color: T.textMuted, lineHeight: 1.7, background: "rgba(0,0,0,0.15)", borderRadius: 8, padding: "14px 16px" }}>
                <strong style={{ color: T.text }}>Analyse:</strong>{" "}
                Bei einem Kaufpreis von <strong style={{ color: T.gold }}>{fmtEUR(inp.kaufpreis)}</strong> und einer
                Jahresnettomiete von <strong style={{ color: T.gold }}>{fmtEUR(inp.jahresmiete)}</strong> ergibt sich ein
                Kaufpreisfaktor von <strong style={{ color: T.text }}>{fmtX(res.faktor)}</strong> und eine Brutto-Rendite
                von <strong style={{ color: res.brutto >= 5 ? T.green : T.yellow }}>{fmtPct(res.brutto)}</strong>.
                {" "}Die Netto-Rendite nach Bewirtschaftungskosten und {inp.leerstand} % Leerstand
                beträgt <strong style={{ color: T.text }}>{fmtPct(res.nettoRend)}</strong>.
                {" "}Der monatliche Cashflow vor Steuer liegt bei <strong style={{ color: res.cfPreM >= 0 ? T.green : T.red }}>{fmtEUR(res.cfPreM)}</strong>.
                {" "}Der DSCR von <strong style={{ color: res.dscr >= 1.2 ? T.green : T.yellow }}>{res.dscr.toFixed(2).replace(".",",")}</strong>{" "}
                {res.dscr >= 1.2 ? "signalisiert solide Bankfähigkeit." : res.dscr >= 1.1 ? "liegt im Grenzbereich — Verhandlungsspielraum beim Zins prüfen." : "ist kritisch — Finanzierung gefährdet."}
                {" "}Der IRR über 10 Jahre beträgt <strong style={{ color: T.text }}>{fmtPct(res.irrVal)}</strong> bei
                einem MOIC von <strong style={{ color: T.text }}>{fmtX(res.moic)}</strong>.
              </div>
            </div>
 
            {/* Detailtabelle */}
            <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: "22px 24px" }}>
              <h3 style={{ fontFamily: T.serif, fontSize: 17, color: T.text, margin: "0 0 18px" }}>Vollständige KPI-Übersicht</h3>
              {[
                { head: "Transaktion", rows: [
                  ["Kaufpreis", fmtEUR(inp.kaufpreis)],
                  ["Kaufnebenkosten (KNK)", fmtEUR(res.knkAbs), `${inp.knk} %`],
                  ["→ Grunderwerbsteuer", fmtEUR(res.grunderwerbsteuer)],
                  ["→ Notar / Grundbuch", fmtEUR(res.notarGrundbuch)],
                  ["→ Makler (est.)", fmtEUR(res.makler)],
                  ["Gesamtinvestition", fmtEUR(res.gesamt), "SUMME"],
                ]},
                { head: "Ertrag & Rendite", rows: [
                  ["Jahresmiete (Brutto)", fmtEUR(inp.jahresmiete)],
                  ["Bewirtschaftungskosten", fmtEUR(res.bewKosten), `-${inp.bew} %`],
                  ["Leerstandsverlust", fmtEUR(res.leerstandAbs), `-${inp.leerstand} %`],
                  ["Instandhaltungsrücklage", fmtEUR(res.ihr), "auto"],
                  ["Nettomietertrag", fmtEUR(res.nettoMiete)],
                  ["NOI (Net Operating Income)", fmtEUR(res.noi)],
                  ["Bruttorendite", fmtPct(res.brutto)],
                  ["Netto-Mietrendite", fmtPct(res.nettoRend)],
                  ["Kapitalisierungsrate (Cap Rate)", fmtPct(res.capRate)],
                  ["Kaufpreisfaktor", fmtX(res.faktor)],
                ]},
                { head: "Finanzierung", rows: [
                  ["Eigenkapital", fmtEUR(res.ekAbs), `${inp.ek} %`],
                  ["Fremdkapital (Darlehen)", fmtEUR(res.fk)],
                  ["LTV (Loan-to-Value)", fmtPct(res.ltv, 1)],
                  ["Sollzinssatz", fmtPct(inp.zins, 1)],
                  ["Zinslast p.a.", fmtEUR(res.zinslast)],
                  ["Tilgung p.a.", fmtEUR(res.tilgAbs), `${inp.tilgung} %`],
                  ["Kapitaldienst gesamt p.a.", fmtEUR(res.kd)],
                  ["DSCR", res.dscr.toFixed(2).replace(".",",")],
                ]},
                { head: "Cashflow & Steuer", rows: [
                  ["AfA p.a.", fmtEUR(res.afa), inp.isDenkmal ? "§7i Denkmal" : `${inp.regAfa} %`],
                  ["Steuerliches Ergebnis p.a.", fmtEUR(res.stlErgebnis)],
                  ["Steuerlast p.a.", fmtEUR(res.steuerlast), `${inp.steuer} % Steuersatz`],
                  ["Cashflow / Monat (vor Steuer)", fmtEUR(res.cfPreM)],
                  ["Cashflow / Monat (nach Steuer)", fmtEUR(res.cfPostM)],
                  ["Break-Even-Miete / Monat", fmtEUR(res.beMonat)],
                ]},
                { head: "Investment-Returns", rows: [
                  ["ROE (Eigenkapitalrendite)", fmtPct(res.roe)],
                  ["ROI (Gesamtkapitalrendite)", fmtPct(res.roi)],
                  ["IRR (10 Jahre)", fmtPct(res.irrVal)],
                  ["NPV (Kapitalwert)", fmtEUR(res.npvVal), `@ ${inp.diskont} % Diskont`],
                  ["MOIC", fmtX(res.moic)],
                  ["EK-Amortisation", res.amort ? fmtYr(res.amort) : "Negativ"],
                ]},
              ].map(({ head, rows }) => (
                <div key={head} style={{ marginBottom: 24 }}>
                  <div style={{ fontSize: 11, color: T.gold, textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: 700, marginBottom: 8, borderBottom: `1px solid ${T.border}`, paddingBottom: 6 }}>
                    {head}
                  </div>
                  {rows.map(([label, value, note], i) => (
                    <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "7px 0", borderBottom: `1px solid ${T.surface3}` }}>
                      <span style={{ color: T.textMuted, fontSize: 13 }}>{label}</span>
                      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                        {note && <span style={{ fontSize: 11, color: T.textDim }}>{note}</span>}
                        <span style={{ fontFamily: T.mono, fontSize: 13, color: T.text }}>{value}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
 
            {/* Disclaimer */}
            <div style={{ background: T.surface2, border: `1px solid ${T.border}`, borderRadius: 10, padding: "16px 20px", marginTop: 16 }}>
              <div style={{ fontSize: 11, color: T.textDim, lineHeight: 1.6 }}>
                <strong style={{ color: T.textMuted }}>Rechtlicher Hinweis:</strong>{" "}
                Die von YieldBase generierten Ergebnisse sind mathematische Modellsimulationen und dienen ausschließlich der Orientierung.
                Sie ersetzen keine rechtliche, steuerliche oder finanzielle Beratung. Berechnungsmethodik orientiert sich an ImmoWertV und deutschen Steuervorschriften.
                © {new Date().getFullYear()} YieldBase Analytics. Alle Rechte vorbehalten.
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
 
