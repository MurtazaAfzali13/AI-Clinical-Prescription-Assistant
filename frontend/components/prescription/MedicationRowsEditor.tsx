"use client";

import { Plus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Medication } from "@/lib/types/prescription";

export const DEFAULT_MEDICATION_ROW_COUNT = 6;

export function emptyMedicationRows(count: number = DEFAULT_MEDICATION_ROW_COUNT): Medication[] {
  return Array.from({ length: count }, () => ({ name: "", dosage: "", frequency: "", duration: "" }));
}

interface MedicationRowsEditorProps {
  medications: Medication[];
  onChange: (medications: Medication[]) => void;
}

export function MedicationRowsEditor({ medications, onChange }: MedicationRowsEditorProps) {
  function updateRow(index: number, field: keyof Medication, value: string) {
    const next = medications.map((med, i) => (i === index ? { ...med, [field]: value } : med));
    onChange(next);
  }

  function removeRow(index: number) {
    onChange(medications.filter((_, i) => i !== index));
  }

  function addRow() {
    onChange([...medications, { name: "", dosage: "", frequency: "", duration: "" }]);
  }

  return (
    <div className="flex flex-col gap-3">
      {medications.map((med, index) => (
        <div key={index} className="relative rounded-lg border border-border bg-background/40 p-3">
          {medications.length > 1 && (
            <button
              type="button"
              onClick={() => removeRow(index)}
              aria-label="Remove medication"
              className="absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded-full text-ink/30 hover:bg-warn-red/10 hover:text-warn-red"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
          <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-ink/40">
            Medication {index + 1}
          </p>
          <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
            <div className="flex flex-col gap-1">
              <Label htmlFor={`med-name-${index}`} className="text-xs font-normal text-ink/60">
                Name
              </Label>
              <Input
                id={`med-name-${index}`}
                value={med.name}
                onChange={(e) => updateRow(index, "name", e.target.value)}
                placeholder="Amlodipine"
                className="h-9 text-sm"
              />
            </div>
            <div className="flex flex-col gap-1">
              <Label htmlFor={`med-dosage-${index}`} className="text-xs font-normal text-ink/60">
                Dosage
              </Label>
              <Input
                id={`med-dosage-${index}`}
                value={med.dosage}
                onChange={(e) => updateRow(index, "dosage", e.target.value)}
                placeholder="5mg"
                className="h-9 text-sm"
              />
            </div>
            <div className="flex flex-col gap-1">
              <Label htmlFor={`med-frequency-${index}`} className="text-xs font-normal text-ink/60">
                Frequency
              </Label>
              <Input
                id={`med-frequency-${index}`}
                value={med.frequency}
                onChange={(e) => updateRow(index, "frequency", e.target.value)}
                placeholder="once daily"
                className="h-9 text-sm"
              />
            </div>
            <div className="flex flex-col gap-1">
              <Label htmlFor={`med-duration-${index}`} className="text-xs font-normal text-ink/60">
                Duration
              </Label>
              <Input
                id={`med-duration-${index}`}
                value={med.duration ?? ""}
                onChange={(e) => updateRow(index, "duration", e.target.value)}
                placeholder="optional"
                className="h-9 text-sm"
              />
            </div>
          </div>
        </div>
      ))}

      <Button type="button" variant="outline" size="sm" onClick={addRow} className="self-start">
        <Plus className="h-3.5 w-3.5" /> Add medication
      </Button>
    </div>
  );
}
