'use client';

import { useMemo, useState } from 'react';
import { TokenSource } from 'livekit-client';
import { useSession } from '@livekit/components-react';
import { WarningIcon } from '@phosphor-icons/react/dist/ssr';
import type { AppConfig } from '@/app-config';
import { AgentSessionProvider } from '@/components/agents-ui/agent-session-provider';
import { StartAudioButton } from '@/components/agents-ui/start-audio-button';
import { ViewController } from '@/components/app/view-controller';
import { DishaSessionProvider } from '@/components/disha/disha-session-provider';
import { Toaster } from '@/components/ui/sonner';
import { useAgentErrors } from '@/hooks/useAgentErrors';
import { useDebugMode } from '@/hooks/useDebug';
import { DISHA_COPY, DishaCopyProvider } from '@/lib/disha-copy';
import {
  DISHA_AGENT_NAME,
  DISHA_CASE_ATTRIBUTE,
  DISHA_LANGUAGE_ATTRIBUTE,
  type DishaLanguage,
} from '@/lib/disha-language';
import { getSandboxTokenSource } from '@/lib/utils';

const IN_DEVELOPMENT = process.env.NODE_ENV !== 'production';

function AppSetup() {
  useDebugMode({ enabled: IN_DEVELOPMENT });
  useAgentErrors();

  return null;
}

interface AppProps {
  appConfig: AppConfig;
}

export function App({ appConfig }: AppProps) {
  const [language, setLanguage] = useState<DishaLanguage>('hi');
  // Stable per-device case id so a returning student resumes their case.
  // Lazy initializer, not an effect: runs once on the client; '' during SSR.
  const [caseId] = useState(() => {
    if (typeof window === 'undefined') return '';
    let id = window.localStorage.getItem('disha.case');
    if (!id) {
      id = `case_${Math.random().toString(36).slice(2, 10)}`;
      window.localStorage.setItem('disha.case', id);
    }
    return id;
  });

  const tokenSource = useMemo(() => {
    // Only use the sandbox source when the endpoint is a NON-EMPTY string. The
    // Docker build defines NEXT_PUBLIC_CONN_DETAILS_ENDPOINT as "" (empty but
    // defined), and `typeof "" === 'string'` is true — which routed the token
    // request into the sandbox source, where `new URL("", origin)` resolves to
    // "/", posts there, and gets the HTML page back ("Error fetching connection
    // details"). A truthy check falls through to the real /api/token route.
    return process.env.NEXT_PUBLIC_CONN_DETAILS_ENDPOINT
      ? getSandboxTokenSource(appConfig, language)
      : TokenSource.endpoint('/api/token');
  }, [appConfig, language]);

  const session = useSession(tokenSource, {
    agentName: DISHA_AGENT_NAME,
    participantAttributes: {
      [DISHA_LANGUAGE_ATTRIBUTE]: language,
      ...(caseId ? { [DISHA_CASE_ATTRIBUTE]: caseId } : {}),
    },
  });

  return (
    <DishaCopyProvider language={language}>
      <AgentSessionProvider session={session}>
        <DishaSessionProvider>
          <AppSetup />
          <main className="grid h-svh grid-cols-1 place-content-center">
            <ViewController
              appConfig={appConfig}
              language={language}
              onLanguageChange={setLanguage}
            />
          </main>
        </DishaSessionProvider>
        <StartAudioButton label={DISHA_COPY[language].panel.startAudio} />
        <Toaster
          icons={{
            warning: <WarningIcon weight="bold" />,
          }}
          position="top-center"
          className="toaster group"
          style={
            {
              '--normal-bg': 'var(--popover)',
              '--normal-text': 'var(--popover-foreground)',
              '--normal-border': 'var(--border)',
            } as React.CSSProperties
          }
        />
      </AgentSessionProvider>
    </DishaCopyProvider>
  );
}
