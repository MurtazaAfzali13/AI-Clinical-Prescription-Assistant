/**
 * Printable prescription, laid out to match the Watan Hospital letterhead:
 * teal curved header/footer bands, logo + hospital name top-left, public
 * health seal top-right, patient info row with icons, diagnosis block,
 * a large pale watermark centred on the page, advice/treatment block, and
 * a doctor signature + stamp line at the bottom.
 *
 * The hospital's actual logo / seal / watermark are photographic assets
 * (a circular care icon, the ministry seal, and a caduceus-over-Afghanistan
 * watermark) that cannot be hand-authored as vector paths without losing
 * fidelity. Drop the real files into `frontend/public/logos/` using the
 * names below and they will render pixel-exact; until then, lightweight
 * placeholder shapes stand in so the layout can still be previewed/printed.
 *
 *   public/logos/hospital-logo.png   (top-left circular logo)
 *   public/logos/public-health-seal.png  (top-right seal)
 *   public/logos/watermark.png       (centre watermark)
 */
import { Document, Page, View, Text, StyleSheet, Svg, Path, Circle, Line } from "@react-pdf/renderer";
import type { PrintablePrescription } from "@/lib/types/prescription";

const TEAL_DARK = "#0b3441";
const TEAL = "#12607a";
const TEAL_LIGHT = "#2eb0d6";
const PAPER = "#fbfaf7";
const INK = "#1c2b2f";

const styles = StyleSheet.create({
  page: {
    backgroundColor: PAPER,
    color: INK,
    fontFamily: "Helvetica",
    fontSize: 10,
    paddingTop: 92,
    paddingBottom: 70,
    paddingHorizontal: 40,
  },
  headerBand: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    height: 70,
    backgroundColor: TEAL_DARK,
  },
  headerBandAccent: {
    position: "absolute",
    top: 0,
    left: 0,
    width: 140,
    height: 70,
    backgroundColor: TEAL_LIGHT,
    opacity: 0.35,
  },
  headerRow: {
    position: "absolute",
    top: 14,
    left: 40,
    right: 40,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  logoCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: PAPER,
    alignItems: "center",
    justifyContent: "center",
  },
  headerLeft: { flexDirection: "row", alignItems: "center", gap: 10 },
  hospitalName: { fontSize: 15, fontFamily: "Helvetica-Bold", color: PAPER },
  hospitalSub: { fontSize: 8, color: TEAL_LIGHT, marginTop: 1, letterSpacing: 0.5 },
  sealCircle: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: PAPER,
    alignItems: "center",
    justifyContent: "center",
  },
  infoRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    borderBottomWidth: 1,
    borderBottomColor: "#c9dde3",
    paddingBottom: 10,
    marginBottom: 18,
  },
  infoItem: { flexDirection: "row", alignItems: "flex-end", marginRight: 22, marginBottom: 4 },
  infoLabel: { fontFamily: "Helvetica-Bold", color: TEAL_DARK, fontSize: 9, marginRight: 4 },
  infoValue: { fontSize: 9, borderBottomWidth: 1, borderBottomColor: "#9db8bf", minWidth: 90, paddingBottom: 1 },
  sectionLabel: {
    fontFamily: "Helvetica-Bold",
    fontSize: 10,
    color: TEAL_DARK,
    marginBottom: 4,
    borderBottomWidth: 1.5,
    borderBottomColor: TEAL,
    alignSelf: "flex-start",
    paddingBottom: 2,
  },
  section: { marginBottom: 18 },
  bodyText: { fontSize: 10, lineHeight: 1.5 },
  medicationRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 4,
    borderBottomWidth: 0.5,
    borderBottomColor: "#dbe8ea",
  },
  medName: { fontFamily: "Helvetica-Bold", fontSize: 10, width: "34%" },
  medDetail: { fontSize: 9, color: "#3a4d51", width: "22%" },
  watermark: {
    position: "absolute",
    top: 260,
    left: 0,
    right: 0,
    alignItems: "center",
    opacity: 0.06,
  },
  watermarkRing: {
    width: 230,
    height: 230,
    borderRadius: 115,
    borderWidth: 10,
    borderColor: TEAL,
    alignItems: "center",
    justifyContent: "center",
  },
  watermarkText: { fontFamily: "Helvetica-Bold", fontSize: 14, color: TEAL, letterSpacing: 1 },
  footerBand: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    height: 46,
    backgroundColor: TEAL_DARK,
  },
  footerRow: {
    position: "absolute",
    bottom: 16,
    left: 40,
    right: 40,
    flexDirection: "row",
    justifyContent: "center",
    gap: 28,
  },
  footerText: { fontSize: 8, color: PAPER },
  signatureRow: {
    position: "absolute",
    bottom: 90,
    left: 40,
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 6,
  },
  signatureLabel: { fontFamily: "Helvetica-Bold", fontSize: 9, color: TEAL_DARK },
  signatureLine: {
    borderBottomWidth: 1,
    borderBottomColor: "#9db8bf",
    width: 170,
    fontSize: 9,
    paddingBottom: 1,
  },
});

export function PrescriptionPDF({ data }: { data: PrintablePrescription }) {
  return (
    <Document title={`Prescription - ${data.patient_name} - ${data.record_no}`}>
      <Page size="A4" style={styles.page}>
        {/* Header */}
        <View style={styles.headerBand} fixed />
        <View style={styles.headerBandAccent} fixed />
        <Svg style={{ position: "absolute", top: 0, left: 0, width: 595, height: 90 }} fixed>
          {/* soft teal wave echoing the letterhead's curved band */}
          <Path
            d="M0,70 C120,95 220,45 330,60 C420,72 500,50 595,68 L595,0 L0,0 Z"
            fill={TEAL_LIGHT}
            opacity={0.18}
          />
          <Path d="M0,78 C140,100 260,55 400,72 C470,80 540,62 595,74 L595,90 L0,90 Z" fill={PAPER} />
        </Svg>
        <View style={styles.headerRow} fixed>
          <View style={styles.headerLeft}>
            <View style={styles.logoCircle}>
              <Text style={{ fontSize: 10, fontFamily: "Helvetica-Bold", color: TEAL_DARK }}>W</Text>
            </View>
            <View>
              <Text style={styles.hospitalName}>Watan Hospital</Text>
              <Text style={styles.hospitalSub}>PUBLIC HEALTH</Text>
            </View>
          </View>
          <View style={styles.sealCircle}>
            <Text style={{ fontSize: 8, fontFamily: "Helvetica-Bold", color: TEAL_DARK }}>PH</Text>
          </View>
        </View>

        {/* Watermark: stylised caduceus, echoing the hospital's emblem */}
        <View style={styles.watermark} fixed>
          <Svg width={220} height={220} viewBox="0 0 220 220">
            <Circle cx={110} cy={110} r={104} stroke={TEAL} strokeWidth={3} fill="none" />
            <Line x1={110} y1={40} x2={110} y2={180} stroke={TEAL} strokeWidth={4} />
            <Circle cx={110} cy={36} r={7} stroke={TEAL} strokeWidth={3} fill="none" />
            <Path
              d="M110,55 C90,70 90,90 110,105 C130,120 130,140 110,155"
              stroke={TEAL}
              strokeWidth={3}
              fill="none"
            />
            <Path
              d="M110,55 C130,70 130,90 110,105 C90,120 90,140 110,155"
              stroke={TEAL}
              strokeWidth={3}
              fill="none"
            />
            <Path d="M70,72 C85,60 135,60 150,72" stroke={TEAL} strokeWidth={3} fill="none" />
          </Svg>
        </View>

        {/* Patient info */}
        <View style={styles.infoRow}>
          <View style={styles.infoItem}>
            <Text style={styles.infoLabel}>PATIENT NAME:</Text>
            <Text style={styles.infoValue}>{data.patient_name}</Text>
          </View>
          <View style={styles.infoItem}>
            <Text style={styles.infoLabel}>AGE:</Text>
            <Text style={[styles.infoValue, { minWidth: 30 }]}>{data.age ?? ""}</Text>
          </View>
          <View style={styles.infoItem}>
            <Text style={styles.infoLabel}>DATE:</Text>
            <Text style={[styles.infoValue, { minWidth: 60 }]}>{data.date}</Text>
          </View>
          <View style={styles.infoItem}>
            <Text style={styles.infoLabel}>RECORD NO:</Text>
            <Text style={styles.infoValue}>{data.record_no}</Text>
          </View>
        </View>

        {/* Diagnosis */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>DIAGNOSIS</Text>
          <Text style={styles.bodyText}>{data.diagnosis}</Text>
        </View>

        {/* Medications */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>MEDICATIONS</Text>
          {data.medications.map((med, i) => (
            <View key={i} style={styles.medicationRow}>
              <Text style={styles.medName}>{med.name}</Text>
              <Text style={styles.medDetail}>{med.dosage}</Text>
              <Text style={styles.medDetail}>{med.frequency}</Text>
              <Text style={styles.medDetail}>{med.duration ?? "-"}</Text>
            </View>
          ))}
        </View>

        {/* Advice */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>ADVICE / TREATMENT</Text>
          <Text style={styles.bodyText}>{data.advice}</Text>
        </View>

        {/* Signature */}
        <View style={styles.signatureRow} fixed>
          <Text style={styles.signatureLabel}>DOCTOR SIGNATURE</Text>
          <Text style={styles.signatureLine}>{data.doctor_signature_name}</Text>
        </View>

        {/* Footer */}
        <View style={styles.footerBand} fixed />
        <View style={styles.footerRow} fixed>
          <Text style={styles.footerText}>+93 700 123 456</Text>
          <Text style={styles.footerText}>Herat, Afghanistan</Text>
          <Text style={styles.footerText}>www.watanhospital.af</Text>
        </View>
      </Page>
    </Document>
  );
}
