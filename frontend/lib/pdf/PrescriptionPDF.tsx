import { Document, Page, View, Text, StyleSheet, Svg, Path, Image } from "@react-pdf/renderer";
import type { PrintablePrescription } from "@/lib/types/prescription";

const TEAL_DARK = "#0a4b60"; 
const TEAL_LIGHT = "#1590a8";
const TEAL_PALE = "#d5e9ee"; 
const PAPER = "#ffffff";
const INK = "#1c2b2f";

const styles = StyleSheet.create({
  page: {
    backgroundColor: PAPER,
    color: INK,
    fontFamily: "Helvetica",
    fontSize: 10,
    paddingTop: 130, 
    paddingBottom: 130, 
    paddingHorizontal: 40,
  },
  backgroundSvg: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: -1,
  },
  // --- Header Styles ---
  headerContainer: {
    position: "absolute",
    top: 25,
    left: 40,
    right: 40,
    flexDirection: "row",
    justifyContent: "space-between", 
    alignItems: "center", 
  },
  logoLeft: {
    width: 75,
    height: 75,
    marginLeft: 100, 
    objectFit: "contain",
  },
  headerRightGroup: {
    flexDirection: "row",
    alignItems: "center",
  },
  logoText: {
    width: 250, // سایز نام شفاخانه بزرگتر شد (قبلا 140 بود)
    height: 140,  // ارتفاع بزرگتر شد (قبلا 55 بود)
    objectFit: "contain",
    marginRight: 5, 
  },
  headerDivider: {
    width: 1.5,
    height: 80, // ارتفاع خط متناسب با لوگوهای جدید بزرگتر شد (قبلا 65 بود)
    backgroundColor: TEAL_DARK, 
    marginRight: 15, 
  },
  logoRight: {
    width: 110, // سایز لوگوی صحت عامه بزرگتر شد (قبلا 85 بود)
    height: 110, 
    objectFit: "contain",
  },
  // --- Patient Info ---
  infoRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    borderBottomWidth: 1.5,
    borderBottomColor: TEAL_LIGHT,
    paddingBottom: 8,
    marginBottom: 30,
  },
  infoItem: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 4,
  },
  infoLabel: {
    fontFamily: "Helvetica-Bold",
    color: TEAL_DARK,
    fontSize: 8,
  },
  infoValue: {
    fontSize: 9,
    borderBottomWidth: 0.5,
    borderBottomColor: "#9db8bf",
    minWidth: 60,
    paddingBottom: 1,
    textAlign: "center",
  },
  // --- Body Sections ---
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: 8,
  },
  sectionTitleContainer: {
    alignItems: "flex-start",
  },
  sectionTitleText: {
    fontFamily: "Helvetica-Bold",
    fontSize: 9,
    color: TEAL_DARK,
  },
  sectionTitleUnderline: {
    width: 15,
    height: 1.5,
    backgroundColor: TEAL_LIGHT,
    marginTop: 2,
  },
  section: {
    marginBottom: 25,
  },
  bodyText: {
    fontSize: 10,
    lineHeight: 1.5,
    marginLeft: 16,
  },
  medicationRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 4,
    borderBottomWidth: 0.5,
    borderBottomColor: TEAL_PALE,
    marginLeft: 16,
  },
  medName: { fontFamily: "Helvetica-Bold", fontSize: 10, width: "34%" },
  medDetail: { fontSize: 9, color: "#3a4d51", width: "22%" },
  // --- Watermark Image ---
  watermarkContainer: {
    position: "absolute",
    top: 220, 
    left: 0,
    right: 0,
    alignItems: "center",
    opacity: 0.09, 
    zIndex: -1,
  },
  watermarkImage: {
    width: 320,
    height: 400,
    objectFit: "contain",
  },
  // --- Footer ---
  signatureRow: {
    position: "absolute",
    bottom: 80,
    left: 40,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  signatureBadge: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: TEAL_DARK,
    alignItems: "center",
    justifyContent: "center",
  },
  signatureLabel: {
    fontFamily: "Helvetica-Bold",
    fontSize: 8,
    color: TEAL_DARK,
  },
  signatureLine: {
    borderBottomWidth: 0.5,
    borderBottomColor: "#9db8bf",
    borderStyle: "dashed",
    width: 150,
    fontSize: 9,
    paddingBottom: 2,
    textAlign: "center",
  },
  footerInfoBar: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    height: 35,
    backgroundColor: TEAL_DARK,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 20,
  },
  footerItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  footerText: {
    fontSize: 8,
    color: PAPER,
  },
  footerDivider: {
    width: 1,
    height: 12,
    backgroundColor: TEAL_LIGHT,
  },
});

export function PrescriptionPDF({ data }: { data: PrintablePrescription }) {
  return (
    <Document title={`Prescription - ${data.patient_name} - ${data.record_no}`}>
      <Page size="A4" style={styles.page}>
        
        {/* --- Background Waves --- */}
        <View style={styles.backgroundSvg} fixed>
          <Svg width="595.28" height="841.89" viewBox="0 0 595.28 841.89">
            <Path d="M0,0 L200,0 C120,20 40,110 0,220 Z" fill={TEAL_DARK} />
            <Path d="M0,240 C30,120 120,40 230,0 L200,0 C120,20 40,110 0,220 Z" fill={TEAL_LIGHT} />
            <Path d="M0,841.89 L595.28,841.89 L595.28,750 C400,810 200,740 0,800 Z" fill={TEAL_DARK} />
            <Path d="M0,780 C200,720 400,790 595.28,730 L595.28,750 C400,810 200,740 0,800 Z" fill={TEAL_LIGHT} />
            <Path d="M470,695 C495,695 510,720 500,745 C480,735 470,715 470,695 Z" fill={TEAL_DARK} />
            <Path d="M440,715 C460,715 475,735 465,755 C450,750 440,735 440,715 Z" fill={TEAL_LIGHT} />
          </Svg>
        </View>

        {/* --- Header Content --- */}
        <View style={styles.headerContainer} fixed>
          {/* لوگوی سمت چپ */}
          <Image 
            src="/logos/logo2.png" 
            style={styles.logoLeft} 
          />

          {/* گروه سمت راست */}
          <View style={styles.headerRightGroup}>
            
            {/* عکس نام شفاخانه */}
            <Image 
              src="/logos/logo4.png" 
              style={styles.logoText} 
            />

            {/* خط جداکننده عمودی */}
            <View style={styles.headerDivider} />

            {/* لوگوی صحت عامه */}
            <Image 
              src="/logos/logo1.png" 
              style={styles.logoRight} 
            />
          </View>
        </View>

        {/* --- Watermark Center Image --- */}
        <View style={styles.watermarkContainer} fixed>
          <Image 
            src="/logos/logo3.png" 
            style={styles.watermarkImage} 
          />
        </View>

        {/* --- Patient Info Row --- */}
        <View style={styles.infoRow}>
          <View style={styles.infoItem}>
            <Svg width={10} height={10} viewBox="0 0 24 24">
              <Path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" fill={TEAL_LIGHT} />
            </Svg>
            <Text style={styles.infoLabel}>PATIENT NAME:</Text>
            <Text style={[styles.infoValue, { minWidth: 100 }]}>{data.patient_name}</Text>
          </View>
          
          <View style={styles.infoItem}>
            <Svg width={10} height={10} viewBox="0 0 24 24">
              <Path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z" fill={TEAL_LIGHT} />
            </Svg>
            <Text style={styles.infoLabel}>AGE:</Text>
            <Text style={[styles.infoValue, { minWidth: 40 }]}>{data.age ?? ""}</Text>
          </View>
          
          <View style={styles.infoItem}>
            <Svg width={10} height={10} viewBox="0 0 24 24">
              <Path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11z" fill={TEAL_LIGHT} />
            </Svg>
            <Text style={styles.infoLabel}>DATE:</Text>
            <Text style={[styles.infoValue, { minWidth: 60 }]}>{data.date}</Text>
          </View>
          
          <View style={styles.infoItem}>
            <Svg width={10} height={10} viewBox="0 0 24 24">
              <Path d="M19 3h-4.18C14.4 1.84 13.3 1 12 1c-1.3 0-2.4.84-2.82 2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 0c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zm2 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z" fill={TEAL_LIGHT} />
            </Svg>
            <Text style={styles.infoLabel}>RECORD NO:</Text>
            <Text style={[styles.infoValue, { minWidth: 70 }]}>{data.record_no}</Text>
          </View>
        </View>

        {/* --- Diagnosis --- */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Svg width={12} height={12} viewBox="0 0 24 24">
              <Path d="M18 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-3 13h-3v3h-2v-3H7v-2h3v-3h2v3h3v2z" fill={TEAL_LIGHT} />
            </Svg>
            <View style={styles.sectionTitleContainer}>
              <Text style={styles.sectionTitleText}>DIAGNOSIS:</Text>
              <View style={styles.sectionTitleUnderline} />
            </View>
          </View>
          <Text style={styles.bodyText}>{data.diagnosis}</Text>
        </View>

        {/* --- Medications --- */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Svg width={12} height={12} viewBox="0 0 24 24">
              <Path d="M20.5 4.5l-2-2c-.78-.78-2.05-.78-2.83 0l-12 12c-.78.78-.78 2.05 0 2.83l2 2c.78.78 2.05.78 2.83 0l12-12c.78-.78.78-2.05 0-2.83zm-14.83 14l-2-2 7-7 2 2-7 7z" fill={TEAL_LIGHT} />
            </Svg>
            <View style={styles.sectionTitleContainer}>
              <Text style={styles.sectionTitleText}>MEDICATIONS:</Text>
              <View style={styles.sectionTitleUnderline} />
            </View>
          </View>
          {data.medications.map((med, i) => (
            <View key={i} style={styles.medicationRow}>
              <Text style={styles.medName}>{med.name}</Text>
              <Text style={styles.medDetail}>{med.dosage}</Text>
              <Text style={styles.medDetail}>{med.frequency}</Text>
              <Text style={styles.medDetail}>{med.duration ?? "-"}</Text>
            </View>
          ))}
        </View>

        {/* --- Advice / Treatment --- */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Svg width={12} height={12} viewBox="0 0 24 24">
              <Path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" fill={TEAL_LIGHT} />
            </Svg>
            <View style={styles.sectionTitleContainer}>
              <Text style={styles.sectionTitleText}>ADVICE / TREATMENT:</Text>
              <View style={styles.sectionTitleUnderline} />
            </View>
          </View>
          <Text style={styles.bodyText}>{data.advice}</Text>
        </View>

        {/* --- Signature --- */}
        <View style={styles.signatureRow} fixed>
          <View style={styles.signatureBadge}>
            <Svg width={14} height={14} viewBox="0 0 24 24">
              <Path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" fill={PAPER} />
            </Svg>
          </View>
          <Text style={styles.signatureLabel}>DOCTOR SIGNATURE</Text>
          <View style={{ alignItems: "center" }}>
            <Text style={styles.signatureLine}>{data.doctor_signature_name}</Text>
            <Text style={{ fontSize: 7, color: "#666", marginTop: 3 }}>(STAMP)</Text>
          </View>
        </View>

        {/* --- Footer Info Bar --- */}
        <View style={styles.footerInfoBar} fixed>
          <View style={styles.footerItem}>
            <Svg width={10} height={10} viewBox="0 0 24 24">
              <Path d="M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z" fill={PAPER} />
            </Svg>
            <Text style={styles.footerText}>+93 783000247</Text>
          </View>
          
          <View style={styles.footerDivider} />
          
          <View style={styles.footerItem}>
            <Svg width={10} height={10} viewBox="0 0 24 24">
              <Path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" fill={PAPER} />
            </Svg>
            <Text style={styles.footerText}>kabul, Afghanistan</Text>
          </View>
          
          <View style={styles.footerDivider} />
          
          <View style={styles.footerItem}>
            <Svg width={10} height={10} viewBox="0 0 24 24">
              <Path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" fill={PAPER} />
            </Svg>
            <Text style={styles.footerText}>www.watanhospital.af</Text>
          </View>
        </View>

      </Page>
    </Document>
  );
}