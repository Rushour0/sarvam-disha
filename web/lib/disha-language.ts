export const DISHA_AGENT_NAME = 'disha';
export const DISHA_LANGUAGE_ATTRIBUTE = 'disha.lang';
export const DISHA_CASE_ATTRIBUTE = 'disha.case';

export const DISHA_LANGUAGES = [
  { value: 'hi', label: 'हिंदी', callLabel: 'दिशा से बात करें' },
  { value: 'en', label: 'English', callLabel: 'Talk to Disha' },
  { value: 'mr', label: 'मराठी', callLabel: 'दिशाशी बोला' },
  { value: 'ta', label: 'தமிழ்', callLabel: 'திஷாவிடம் பேசுங்கள்' },
] as const;

export type DishaLanguage = (typeof DISHA_LANGUAGES)[number]['value'];

/**
 * Languages actually offered in the UI picker.
 *
 * The student base is Maharashtra tier-3/4, so Hindi, English and Marathi are
 * offered as starting languages. Tamil copy remains unreviewed, so it stays out
 * of the picker. The agent still follows the student into any language it
 * detects mid-call — this only fixes the starting language.
 */
export const DISHA_PICKER_LANGUAGES = DISHA_LANGUAGES.filter(
  (language): language is (typeof DISHA_LANGUAGES)[number] & { value: 'hi' | 'en' | 'mr' } =>
    language.value === 'hi' || language.value === 'en' || language.value === 'mr'
);

export function isDishaLanguage(value: unknown): value is DishaLanguage {
  return DISHA_LANGUAGES.some((language) => language.value === value);
}
