'use client';

import { type FormEvent, useId, useState } from 'react';
import { CheckCircle2 } from 'lucide-react';
import { useRoomContext } from '@livekit/components-react';
import { Button } from '@/components/ui/button';
import { DISHA_CLIENT_TOPIC } from '@/lib/disha-events';
import { cn } from '@/lib/shadcn/utils';

interface SignupCardProps {
  prominent: boolean;
  onSignedUp?: () => void;
}

export function SignupCard({ prominent, onSignedUp }: SignupCardProps) {
  const room = useRoomContext();
  const phoneId = useId();
  const errorId = `${phoneId}-error`;
  const [phone, setPhone] = useState('');
  const [attempted, setAttempted] = useState(false);
  const [saved, setSaved] = useState(false);
  const isValid = phone.length === 10;
  const showError = attempted && !isValid;

  const handleSignup = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAttempted(true);
    if (!isValid) return;

    const fullPhone = `+91${phone}`;
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
      window.localStorage.setItem('disha.case', `case_91${phone}`);
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
      <h2 className="font-semibold">और गहराई से जानना है?</h2>
      <p className="text-muted-foreground mt-2 text-sm leading-6">
        मोबाइल नंबर दीजिए — Disha आपकी प्रगति याद रखेगी और अगली बातचीत वहीं से शुरू होगी।
      </p>
      <form className="mt-3" noValidate onSubmit={handleSignup}>
        <label htmlFor={phoneId} className="text-sm font-medium">
          मोबाइल नंबर
        </label>
        <div
          className={cn(
            'border-border bg-background focus-within:ring-ring mt-2 flex min-h-11 items-center rounded-full border focus-within:ring-2',
            showError && 'border-destructive'
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
              if (nextPhone.length === 10) setAttempted(false);
            }}
            onBlur={() => {
              if (phone.length > 0 && !isValid) setAttempted(true);
            }}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !isValid) setAttempted(true);
            }}
            placeholder="10 अंकों का नंबर"
            maxLength={10}
            pattern="[0-9]{10}"
            required
            aria-invalid={showError}
            aria-describedby={showError ? errorId : undefined}
            className="focus-visible:ring-ring min-h-11 min-w-0 flex-1 rounded-r-full bg-transparent px-3 text-base outline-none focus-visible:ring-2"
          />
        </div>
        {showError && (
          <p id={errorId} role="alert" className="text-destructive mt-2 text-xs">
            कृपया 10 अंकों का सही मोबाइल नंबर डालें।
          </p>
        )}
        <Button
          type="submit"
          disabled={!isValid}
          className="focus-visible:ring-ring mt-2 min-h-11 w-full rounded-full focus-visible:ring-2"
        >
          मोबाइल नंबर सुरक्षित करें
        </Button>
      </form>
    </aside>
  );
}
