'use client';

import { type FormEvent, useId, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/shadcn/utils';

// DEMO ONLY: mirrors the hardcoded OTP in signup-card.tsx; both stand in for a
// real SMS provider and must be replaced before any real user traffic.
const DEMO_OTP = '123456';

interface LoginCardProps {
  title: string;
  body: string;
}

/**
 * Phone + OTP login for pages that live outside a call — /me and /explore.
 *
 * Unlike SignupCard this has no LiveKit room to notify; it only needs the
 * signed session cookie that POST /api/disha/signup sets, then a server
 * re-render to pick it up.
 */
export function LoginCard({ title, body }: LoginCardProps) {
  const router = useRouter();
  const phoneId = useId();
  const otpId = useId();
  const otpHintId = `${otpId}-hint`;
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [step, setStep] = useState<'phone' | 'otp'>('phone');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const isPhoneValid = phone.length === 10;

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');

    if (step === 'phone') {
      if (!isPhoneValid) {
        setError('कृपया 10 अंकों का सही मोबाइल नंबर डालें।');
        return;
      }
      setStep('otp');
      return;
    }

    if (otp !== DEMO_OTP) {
      setError('OTP सही नहीं है। फिर से कोशिश करें।');
      return;
    }

    setSubmitting(true);
    const caseId = `case_91${phone}`;
    try {
      const response = await fetch('/api/disha/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ case: caseId, phone }),
      });
      if (!response.ok) {
        setError('अभी login नहीं हो पाया। थोड़ी देर बाद फिर कोशिश करें।');
        return;
      }
      // The device now resumes this student's case in the next call too.
      try {
        window.localStorage.setItem('disha.case', caseId);
      } catch {
        // Login still completes when storage is unavailable.
      }
      router.refresh();
    } catch {
      setError('अभी login नहीं हो पाया। थोड़ी देर बाद फिर कोशिश करें।');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <aside className="border-disha-leaf bg-disha-leaf/10 rounded-[1.5rem] border-2 p-5">
      <h2 className="font-semibold">{title}</h2>
      <p className="text-muted-foreground mt-2 text-sm leading-6">{body}</p>
      <form className="mt-3" noValidate onSubmit={(event) => void handleSubmit(event)}>
        {step === 'phone' ? (
          <>
            <label htmlFor={phoneId} className="text-sm font-medium">
              मोबाइल नंबर
            </label>
            <div className="border-border bg-background focus-within:ring-ring mt-2 flex min-h-11 items-center rounded-full border focus-within:ring-2">
              <span className="text-muted-foreground border-border ml-4 border-r pr-3 text-sm">
                +91
              </span>
              <input
                id={phoneId}
                type="tel"
                inputMode="numeric"
                autoComplete="tel-national"
                value={phone}
                onChange={(event) => setPhone(event.target.value.replace(/\D/g, '').slice(0, 10))}
                placeholder="10 अंकों का नंबर"
                maxLength={10}
                required
                className="focus-visible:ring-ring min-h-11 min-w-0 flex-1 rounded-r-full bg-transparent px-3 text-base outline-none focus-visible:ring-2 focus-visible:ring-offset-2"
              />
            </div>
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
                  setError('');
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
              onChange={(event) => setOtp(event.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder="OTP डालें"
              maxLength={6}
              required
              aria-describedby={otpHintId}
              className={cn(
                'border-border bg-background focus-visible:ring-ring mt-2 min-h-11 w-full rounded-full border px-4 text-base outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
                error && 'border-destructive'
              )}
            />
            <p id={otpHintId} className="text-muted-foreground mt-2 text-xs">
              डेमो OTP: <span className="font-mono font-semibold">123456</span>
            </p>
            <Button
              type="submit"
              disabled={otp.length !== 6 || submitting}
              className="focus-visible:ring-ring mt-2 min-h-11 w-full rounded-full focus-visible:ring-2 focus-visible:ring-offset-2"
            >
              {submitting ? 'जाँच हो रही है…' : 'OTP सत्यापित करें'}
            </Button>
          </>
        )}
        {error && (
          <p role="alert" className="text-destructive mt-2 text-xs">
            {error}
          </p>
        )}
      </form>
    </aside>
  );
}
