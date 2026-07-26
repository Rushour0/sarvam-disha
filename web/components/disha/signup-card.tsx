'use client';

import { type FormEvent, type ReactNode, useId, useState } from 'react';
import { CheckCircle2 } from 'lucide-react';
import { useRoomContext } from '@livekit/components-react';
import { Button } from '@/components/ui/button';
import { DISHA_CLIENT_TOPIC } from '@/lib/disha-events';
import { cn } from '@/lib/shadcn/utils';

interface SignupCardProps {
  prominent: boolean;
  onSignedUp?: () => void;
  /** Override the pitch when the card is asking for the number in a specific
   *  context — the reference gate explains what unlocking actually gives. */
  title?: string;
  body?: string;
  /** Extra control rendered under the form, e.g. a "show me anyway" escape. */
  footer?: ReactNode;
}

// DEMO ONLY: This hardcoded OTP stands in for a real SMS provider and must be
// replaced before any real user traffic.
const DEMO_OTP = '123456';

async function persistSignup(caseId: string, phone: string): Promise<void> {
  const configuredBase = process.env.NEXT_PUBLIC_DISHA_API?.trim();
  if (!configuredBase) return;

  const base = configuredBase.replace(/\/+$/, '');
  for (let attempt = 0; attempt < 2; attempt += 1) {
    if (attempt > 0) {
      await new Promise((resolve) => window.setTimeout(resolve, 750));
    }

    try {
      const response = await fetch(`${base}/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ case: caseId, phone }),
      });
      if (response.ok) return;
    } catch {
      // Local completion is authoritative; retry once without alarming the student.
    }
  }
}

export function SignupCard({ prominent, onSignedUp, title, body, footer }: SignupCardProps) {
  const room = useRoomContext();
  const phoneId = useId();
  const phoneErrorId = `${phoneId}-error`;
  const otpId = useId();
  const otpHintId = `${otpId}-hint`;
  const otpErrorId = `${otpId}-error`;
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [step, setStep] = useState<'phone' | 'otp'>('phone');
  const [phoneAttempted, setPhoneAttempted] = useState(false);
  const [otpAttempted, setOtpAttempted] = useState(false);
  const [saved, setSaved] = useState(false);
  const isPhoneValid = phone.length === 10;
  const showPhoneError = phoneAttempted && !isPhoneValid;
  const showOtpError = otpAttempted && otp !== DEMO_OTP;

  const handleSignup = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (step === 'phone') {
      setPhoneAttempted(true);
      if (!isPhoneValid) return;
      setStep('otp');
      return;
    }

    setOtpAttempted(true);
    if (otp !== DEMO_OTP) return;

    const fullPhone = `+91${phone}`;
    const caseId = `case_91${phone}`;
    const entry = { phone: fullPhone, ts: Date.now() };
    let existing: unknown = [];

    try {
      existing = JSON.parse(window.localStorage.getItem('disha.signups') ?? '[]');
    } catch {
      existing = [];
    }

    try {
      const signups = Array.isArray(existing) ? existing : [];
      window.localStorage.setItem('disha.signups', JSON.stringify([...signups, entry]));
    } catch {
      // Signup still completes when storage is unavailable.
    }

    try {
      window.localStorage.setItem('disha.case', caseId);
    } catch {
      // Signup still completes when storage is unavailable.
    }

    setSaved(true);
    onSignedUp?.();
    void persistSignup(caseId, phone);

    const payload = new TextEncoder().encode(JSON.stringify({ type: 'signup' }));
    void room.localParticipant
      .publishData(payload, { reliable: true, topic: DISHA_CLIENT_TOPIC })
      .catch(() => {
        // The local signup is authoritative when the data channel is unavailable.
      });
  };

  if (saved) {
    return (
      <aside
        aria-live="polite"
        className="border-disha-leaf/35 bg-disha-leaf/10 rounded-[1.5rem] border p-5"
      >
        <CheckCircle2 className="text-disha-leaf size-6" aria-hidden="true" />
        <h2 className="mt-3 font-semibold">धन्यवाद!</h2>
        <p className="text-muted-foreground mt-2 text-sm leading-6">
          हम आपसे जल्द संपर्क करेंगे। तब तक अपनी चुनी हुई सूची परिवार के साथ ज़रूर देखें।
        </p>
      </aside>
    );
  }

  return (
    <aside
      className={cn(
        'rounded-[1.5rem] border p-5',
        prominent ? 'border-disha-leaf bg-disha-leaf/10 border-2' : 'border-border/70 bg-card'
      )}
    >
      <h2 className="font-semibold">{title ?? 'और गहराई से जानना है?'}</h2>
      <p className="text-muted-foreground mt-2 text-sm leading-6">
        {body ??
          'मोबाइल नंबर दीजिए — Disha आपकी प्रगति याद रखेगी और अगली बातचीत वहीं से शुरू होगी।'}
      </p>
      <form className="mt-3" noValidate onSubmit={handleSignup}>
        {step === 'phone' ? (
          <>
            <label htmlFor={phoneId} className="text-sm font-medium">
              मोबाइल नंबर
            </label>
            <div
              className={cn(
                'border-border bg-background focus-within:ring-ring mt-2 flex min-h-11 items-center rounded-full border focus-within:ring-2',
                showPhoneError && 'border-destructive'
              )}
            >
              <span className="text-muted-foreground border-border ml-4 border-r pr-3 text-sm">
                +91
              </span>
              <input
                id={phoneId}
                type="tel"
                inputMode="numeric"
                autoComplete="tel-national"
                value={phone}
                onChange={(event) => {
                  const nextPhone = event.target.value.replace(/\D/g, '').slice(0, 10);
                  setPhone(nextPhone);
                  if (nextPhone.length === 10) setPhoneAttempted(false);
                }}
                onBlur={() => {
                  if (phone.length > 0 && !isPhoneValid) setPhoneAttempted(true);
                }}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !isPhoneValid) setPhoneAttempted(true);
                }}
                placeholder="10 अंकों का नंबर"
                maxLength={10}
                pattern="[0-9]{10}"
                required
                aria-invalid={showPhoneError}
                aria-describedby={showPhoneError ? phoneErrorId : undefined}
                className="focus-visible:ring-ring min-h-11 min-w-0 flex-1 rounded-r-full bg-transparent px-3 text-base outline-none focus-visible:ring-2 focus-visible:ring-offset-2"
              />
            </div>
            {showPhoneError && (
              <p id={phoneErrorId} role="alert" className="text-destructive mt-2 text-xs">
                कृपया 10 अंकों का सही मोबाइल नंबर डालें।
              </p>
            )}
            <Button
              type="submit"
              disabled={!isPhoneValid}
              className="focus-visible:ring-ring mt-2 min-h-11 w-full rounded-full focus-visible:ring-2 focus-visible:ring-offset-2"
            >
              आगे बढ़ें
            </Button>
          </>
        ) : (
          <>
            <div className="flex min-h-11 items-center justify-between gap-3">
              <p className="text-sm font-medium">+91 {phone}</p>
              <button
                type="button"
                onClick={() => {
                  setStep('phone');
                  setOtp('');
                  setOtpAttempted(false);
                }}
                className="text-disha-leaf focus-visible:ring-ring min-h-11 rounded-full px-3 text-sm font-semibold underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
              >
                बदलें
              </button>
            </div>
            <label htmlFor={otpId} className="mt-2 block text-sm font-medium">
              6 अंकों का OTP
            </label>
            <input
              id={otpId}
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              value={otp}
              onChange={(event) => {
                setOtp(event.target.value.replace(/\D/g, '').slice(0, 6));
                setOtpAttempted(false);
              }}
              placeholder="OTP डालें"
              maxLength={6}
              pattern="[0-9]{6}"
              required
              aria-invalid={showOtpError}
              aria-describedby={showOtpError ? `${otpHintId} ${otpErrorId}` : otpHintId}
              className={cn(
                'border-border bg-background focus-visible:ring-ring mt-2 min-h-11 w-full rounded-full border px-4 text-base outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
                showOtpError && 'border-destructive'
              )}
            />
            <p id={otpHintId} className="text-muted-foreground mt-2 text-xs">
              डेमो OTP: <span className="font-mono font-semibold">123456</span>
            </p>
            {showOtpError && (
              <p id={otpErrorId} role="alert" className="text-destructive mt-2 text-xs">
                OTP सही नहीं है। फिर से कोशिश करें।
              </p>
            )}
            <Button
              type="submit"
              disabled={otp.length !== 6}
              className="focus-visible:ring-ring mt-2 min-h-11 w-full rounded-full focus-visible:ring-2 focus-visible:ring-offset-2"
            >
              OTP सत्यापित करें
            </Button>
          </>
        )}
      </form>
      {footer}
    </aside>
  );
}
