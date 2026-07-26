'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useDataChannel, useSessionContext } from '@livekit/components-react';
import {
  DISHA_TOPIC,
  type DishaEvent,
  type DishaSessionSnapshot,
  decodeDishaPayload,
  deriveDishaSnapshot,
  readStoredSession,
  writeStoredSession,
} from '@/lib/disha-events';

interface DishaSessionContextValue {
  roomName: string;
  events: DishaEvent[];
  snapshot: DishaSessionSnapshot;
  resetView: () => void;
}

const DishaSessionContext = createContext<DishaSessionContextValue | null>(null);

export function DishaSessionProvider({ children }: { children: React.ReactNode }) {
  const session = useSessionContext();
  const [roomName, setRoomName] = useState('');
  const [events, setEvents] = useState<DishaEvent[]>([]);
  const loadedRoomRef = useRef('');

  const handleMessage = useCallback(
    (message: { payload: Uint8Array }) => {
      const event = decodeDishaPayload(message.payload);
      if (!event) return;

      const activeRoom = session.room.name || roomName;
      if (activeRoom) setRoomName(activeRoom);
      setEvents((currentEvents) => [...currentEvents, event]);
    },
    [roomName, session.room]
  );

  useDataChannel(DISHA_TOPIC, handleMessage);

  useEffect(() => {
    const activeRoom = session.room.name;
    if (!activeRoom || loadedRoomRef.current === activeRoom) return;

    loadedRoomRef.current = activeRoom;
    setRoomName(activeRoom);
    setEvents(readStoredSession(activeRoom)?.events ?? []);
  }, [session.connectionState, session.room]);

  useEffect(() => {
    writeStoredSession(roomName, events);
  }, [events, roomName]);

  const snapshot = useMemo(() => deriveDishaSnapshot(events), [events]);
  const resetView = useCallback(() => setEvents([]), []);
  const value = useMemo(
    () => ({ roomName, events, snapshot, resetView }),
    [events, resetView, roomName, snapshot]
  );

  return <DishaSessionContext.Provider value={value}>{children}</DishaSessionContext.Provider>;
}

export function useDishaSession() {
  const context = useContext(DishaSessionContext);
  if (!context) {
    throw new Error('useDishaSession must be used inside DishaSessionProvider');
  }
  return context;
}
