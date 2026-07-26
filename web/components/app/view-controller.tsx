'use client';

import { useEffect, useRef, useState } from 'react';
import { useTheme } from 'next-themes';
import { AnimatePresence, motion } from 'motion/react';
import { useSessionContext } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { AgentSessionView_01 } from '@/components/agents-ui/blocks/agent-session-view-01';
import { WelcomeView } from '@/components/app/welcome-view';
import { useDishaSession } from '@/components/disha/disha-session-provider';
import { SummaryScreen } from '@/components/disha/summary-screen';
import type { DishaSessionSnapshot, SummaryEvent } from '@/lib/disha-events';
import type { DishaLanguage } from '@/lib/disha-language';

const MotionWelcomeView = motion.create(WelcomeView);
const MotionSessionView = motion.create(AgentSessionView_01);

const VIEW_MOTION_PROPS = {
  variants: {
    visible: {
      opacity: 1,
    },
    hidden: {
      opacity: 0,
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.5,
    ease: 'linear',
  },
};

interface ViewControllerProps {
  appConfig: AppConfig;
  language: DishaLanguage;
  onLanguageChange: (language: DishaLanguage) => void;
}

interface EndedSession {
  durationMs: number;
  summary: SummaryEvent;
}

function createDisconnectSummary(snapshot: DishaSessionSnapshot): SummaryEvent {
  const constraintCount = Object.keys(snapshot.constraints).length;
  const summaryHi =
    constraintCount > 0
      ? `आज की बातचीत में आपकी ${constraintCount} ज़रूरी परिस्थिति समझ में आई। इन्हें साथ रखकर अगला कदम चुनें।`
      : 'आज की बातचीत यहीं रुकी। जब तैयार हों, अपनी पसंद और परिस्थिति पर फिर आराम से बात कर सकते हैं।';

  return {
    type: 'summary',
    ts: Date.now(),
    summary_hi: summaryHi,
    shortlist: snapshot.careerPaths,
    next_steps: [
      'आज की बातों में जो सबसे ज़रूरी लगा, उसे लिख लें।',
      snapshot.careerPaths.length > 0
        ? 'Shortlist में से एक रास्ते की फीस, दूरी और eligibility verify करें।'
        : 'अगली बातचीत में अपनी पसंद का एक subject या काम लेकर आएँ।',
    ],
  };
}

export function ViewController({ appConfig, language, onLanguageChange }: ViewControllerProps) {
  const { isConnected, start, end } = useSessionContext();
  const { snapshot, resetView } = useDishaSession();
  const { resolvedTheme } = useTheme();
  const [endedSession, setEndedSession] = useState<EndedSession | null>(null);
  const wasConnectedRef = useRef(false);
  const callStartedAtRef = useRef<number | null>(null);

  useEffect(() => {
    if (isConnected && !wasConnectedRef.current) {
      callStartedAtRef.current = Date.now();
      setEndedSession(null);
    } else if (!isConnected && wasConnectedRef.current) {
      const durationMs = callStartedAtRef.current ? Date.now() - callStartedAtRef.current : 0;
      setEndedSession({
        durationMs,
        summary: createDisconnectSummary(snapshot),
      });
    }

    wasConnectedRef.current = isConnected;
  }, [isConnected, snapshot]);

  const summary = snapshot.summary ?? endedSession?.summary;
  const callDurationMs =
    endedSession?.durationMs ??
    (snapshot.summary && callStartedAtRef.current ? Date.now() - callStartedAtRef.current : 0);

  const handleNewSession = () => {
    callStartedAtRef.current = null;
    setEndedSession(null);
    resetView();
  };

  return (
    <AnimatePresence mode="wait">
      {summary && (
        <SummaryScreen
          key="summary"
          summary={summary}
          callDurationMs={callDurationMs}
          isConnected={isConnected}
          onEndCall={() => void end()}
          onNewSession={handleNewSession}
        />
      )}
      {/* Welcome view */}
      {!summary && !isConnected && (
        <MotionWelcomeView
          key="welcome"
          {...VIEW_MOTION_PROPS}
          language={language}
          onLanguageChange={onLanguageChange}
          onStartCall={() =>
            start({
              tracks: {
                microphone: {
                  enabled: true,
                  publishOptions: { preConnectBuffer: true },
                },
              },
            })
          }
        />
      )}
      {/* Session view */}
      {!summary && isConnected && (
        <MotionSessionView
          key="session-view"
          {...VIEW_MOTION_PROPS}
          supportsChatInput={appConfig.supportsChatInput}
          supportsVideoInput={appConfig.supportsVideoInput}
          supportsScreenShare={appConfig.supportsScreenShare}
          isPreConnectBufferEnabled={appConfig.isPreConnectBufferEnabled}
          audioVisualizerType={appConfig.audioVisualizerType}
          audioVisualizerColor={
            resolvedTheme === 'dark'
              ? appConfig.audioVisualizerColorDark
              : appConfig.audioVisualizerColor
          }
          audioVisualizerColorShift={appConfig.audioVisualizerColorShift}
          audioVisualizerBarCount={appConfig.audioVisualizerBarCount}
          audioVisualizerGridRowCount={appConfig.audioVisualizerGridRowCount}
          audioVisualizerGridColumnCount={appConfig.audioVisualizerGridColumnCount}
          audioVisualizerRadialBarCount={appConfig.audioVisualizerRadialBarCount}
          audioVisualizerRadialRadius={appConfig.audioVisualizerRadialRadius}
          audioVisualizerWaveLineWidth={appConfig.audioVisualizerWaveLineWidth}
          className="fixed inset-0"
        />
      )}
    </AnimatePresence>
  );
}
