"use client";

import { useState } from "react";
import { AlertTriangle, CheckCircle2, Loader2, Send, Share2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, patientsApi } from "@/lib/api/client";

export function ReferPatientForm() {
  const [recordNo, setRecordNo] = useState("");
  const [toDoctorEmail, setToDoctorEmail] = useState("");
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setResult(null);
    setIsSubmitting(true);

    try {
      const response = await patientsApi.refer({
        patient_record_no: recordNo.trim(),
        to_doctor_email: toDoctorEmail.trim(),
        reason: reason.trim() || undefined,
      });
      setResult({ success: response.success, message: response.message });
      if (response.success) {
        setRecordNo("");
        setToDoctorEmail("");
        setReason("");
      }
    } catch (err) {
      setResult({
        success: false,
        message: err instanceof ApiError ? err.message : "Could not send this referral. Please try again.",
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Share2 className="h-4 w-4 text-clinic-600" />
          Share a patient
        </CardTitle>
        <p className="text-xs text-ink/60">
          Refer a patient you currently treat to another doctor by email. They&rsquo;ll gain access to
          the patient&rsquo;s full record. You must already have an active treatment relationship with
          this patient.
        </p>
      </CardHeader>
      <CardContent>
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="refer-record-no">Patient record no.</Label>
            <Input
              id="refer-record-no"
              value={recordNo}
              onChange={(e) => setRecordNo(e.target.value)}
              placeholder="REC-0142"
              required
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="refer-doctor-email">Colleague&rsquo;s email</Label>
            <Input
              id="refer-doctor-email"
              type="email"
              value={toDoctorEmail}
              onChange={(e) => setToDoctorEmail(e.target.value)}
              placeholder="colleague@watanhospital.af"
              required
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="refer-reason">Reason (optional)</Label>
            <Textarea
              id="refer-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Specialist opinion for uncontrolled hypertension"
              className="min-h-[70px]"
            />
          </div>

          {result && (
            <div
              className={`flex items-start gap-2 rounded-md border p-3 text-sm ${
                result.success
                  ? "border-clinic-200 bg-clinic-50 text-clinic-800"
                  : "border-warn-red/30 bg-warn-red/5 text-warn-red"
              }`}
            >
              {result.success ? (
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
              ) : (
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              )}
              <span>{result.message}</span>
            </div>
          )}

          <Button type="submit" disabled={isSubmitting} className="self-start">
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Sending referral...
              </>
            ) : (
              <>
                <Send className="h-4 w-4" /> Send referral
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
