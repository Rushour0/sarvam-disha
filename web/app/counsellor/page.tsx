import type { Metadata } from 'next';
import { CounsellorView } from '@/components/disha/counsellor-view';

export const metadata: Metadata = {
  title: 'Counsellor view — Disha',
  description: 'Disha session constraints and wellbeing notes for counsellor review.',
};

export default function CounsellorPage() {
  return <CounsellorView />;
}
