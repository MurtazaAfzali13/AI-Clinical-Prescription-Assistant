"use client";

import { useRef, useState } from "react";
import { AlertTriangle, Loader2, Mic, Square } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ApiError, transcriptionApi } from "@/lib/api/client";

interface VoiceRecorderButtonProps {
  onTranscript: (text: string) => void;
}

type RecorderState = "idle" | "recording" | "transcribing";

export function VoiceRecorderButton({ onTranscript }: VoiceRecorderButtonProps) {
  const [state, setState] = useState<RecorderState>("idle");
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  async function startRecording() {
    setError(null);

    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Voice input isn't supported in this browser.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];

      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };

      recorder.onstop = async () => {
        streamRef.current?.getTracks().forEach((track) => track.stop());
        const audioBlob = new Blob(chunksRef.current, { type: "audio/webm" });

        if (audioBlob.size === 0) {
          setState("idle");
          return;
        }

        setState("transcribing");
        try {
          const result = await transcriptionApi.transcribe(audioBlob);
          onTranscript(result.text);
        } catch (err) {
          setError(err instanceof ApiError ? err.message : "Could not transcribe that recording.");
        } finally {
          setState("idle");
        }
      };

      recorder.start();
      setState("recording");
    } catch {
      setError("Microphone access was denied. Please allow it to use voice input.");
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
  }

  return (
    <div className="flex flex-col gap-1.5">
      <Button
        type="button"
        variant={state === "recording" ? "destructive" : "outline"}
        size="sm"
        onClick={state === "recording" ? stopRecording : startRecording}
        disabled={state === "transcribing"}
      >
        {state === "recording" ? (
          <>
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-white opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-white" />
            </span>
            <Square className="h-3.5 w-3.5" /> Stop recording
          </>
        ) : state === "transcribing" ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" /> Transcribing...
          </>
        ) : (
          <>
            <Mic className="h-4 w-4" /> Dictate note
          </>
        )}
      </Button>
      {error && (
        <p className="flex items-center gap-1.5 text-xs text-warn-red">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" /> {error}
        </p>
      )}
    </div>
  );
}
