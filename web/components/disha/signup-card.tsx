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

type OtpResponse = { ok?: boolean; error?: string };

type ErrorKind = 'none' | 'phone_rate' | 'phone_send' | 'otp_invalid' | 'otp_rate' | 'otp_fail';

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
  const [submitting, setSubmitting] = useState(false);
  const [errorKind, setErrorKind] = useState<ErrorKind>('none');
  const [saved, setSaved] = useState(false);
  const isPhoneValid = phone.length === 10;
  const showPhoneError =
    (phoneAttempted && !isPhoneValid) || errorKind === 'phone_rate' || errorKind === 'phone_send';
  const showOtpError =
    errorKind === 'otp_invalid' || errorKind === 'otp_rate' || errorKind === 'otp_fail';

  const startOtp = async (): Promise<'ok' | 'rate' | 'fail'> => {
    try {
      const res = await fetch('/api/disha/otp/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone }),
      });
      const data = (await res.json().catch(() => ({}))) as OtpResponse;
      if (res.ok && data.ok) return 'ok';
      if (res.status === 429) return 'rate';
      return 'fail';
    } catch {
      return 'fail';
    }
  };

  const completeSignup = () => {
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

    const payload = new TextEncoder().encode(JSON.stringify({ type: 'signup' }));
    void room.localParticipant
      .publishData(payload, { reliable: true, topic: DISHA_CLIENT_TOPIC })
      .catch(() => {
        // The local signup is authoritative when the data channel is unavailable.
      });
  };

  const handleSignup = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (submitting) return;

    if (step === 'phone') {
      setPhoneAttempted(true);
      if (!isPhoneValid) return;
      setErrorKind('none');
      setSubmitting(true);
      const result = await startOtp();
      setSubmitting(false);
      if (result === 'ok') {
        setStep('otp');
      } else {
        setErrorKind(result === 'rate' ? 'phone_rate' : 'phone_send');
      }
      return;
    }

    setErrorKind('none');
    setSubmitting(true);
    try {
      const res = await fetch('/api/disha/otp/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, code: otp }),
      });
      const data = (await res.json().catch(() => ({}))) as OtpResponse;
      if (res.ok && data.ok) {
        completeSignup();
      } else if (res.status === 400) {
        setErrorKind('otp_invalid');
      } else if (res.status === 429) {
        setErrorKind('otp_rate');
      } else {
        setErrorKind('otp_fail');
      }
    } catch {
      setErrorKind('otp_fail');
    } finally {
      setSubmitting(false);
    }
  };

  const handleResend = async () => {
    if (submitting) return;
    setErrorKind('none');
    setSubmitting(true);
    const result = await startOtp();
    setSubmitting(false);
    if (result === 'rate') {
      setErrorKind('otp_rate');
    } else if (result === 'fail') {
      setErrorKind('otp_fail');
    }
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
                  if (errorKind === 'phone_rate' || errorKind === 'phone_send')
                    setErrorKind('none');
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
                {errorKind === 'phone_rate'
                  ? 'बहुत अधिक कोशिशें। थोड़ी देर बाद फिर कोशिश करें।'
                  : errorKind === 'phone_send'
                    ? 'OTP भेजने में समस्या हुई। थोड़ी देर बाद फिर कोशिश करें।'
                    : 'कृपया 10 अंकों का सही मोबाइल नंबर डालें।'}
              </p>
            )}
            <Button
              type="submit"
              disabled={!isPhoneValid || submitting}
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
                  setPhoneAttempted(false);
                  setErrorKind('none');
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
                if (showOtpError) setErrorKind('none');
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
              +91 {phone} पर OTP भेजा गया।
            </p>
            {showOtpError && (
              <p id={otpErrorId} role="alert" className="text-destructive mt-2 text-xs">
                {errorKind === 'otp_rate'
                  ? 'बहुत अधिक कोशिशें। थोड़ी देर बाद फिर कोशिश करें।'
                  : errorKind === 'otp_fail'
                    ? 'अभी पूरा नहीं हो पाया। थोड़ी देर बाद फिर कोशिश करें।'
                    : 'OTP सही नहीं है। फिर से कोशिश करें।'}
              </p>
            )}
            <Button
              type="submit"
              disabled={otp.length !== 6 || submitting}
              className="focus-visible:ring-ring mt-2 min-h-11 w-full rounded-full focus-visible:ring-2 focus-visible:ring-offset-2"
            >
              OTP सत्यापित करें
            </Button>
            <button
              type="button"
              onClick={handleResend}
              disabled={submitting}
              className="text-disha-leaf focus-visible:ring-ring mt-2 min-h-11 rounded-full px-3 text-sm font-semibold underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
            >
              OTP फिर से भेजें
            </button>
          </>
        )}
      </form>
      {footer}
    </aside>
  );
}
