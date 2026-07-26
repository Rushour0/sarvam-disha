import Image from 'next/image';
import { cn } from '@/lib/shadcn/utils';

export function DishaBrand({
  className,
  showTagline = true,
}: {
  className?: string;
  /**
   * The landing page uses this same line as its `<h1>`. Repeating it in the
   * header inside one viewport reads as unedited, so that surface opts out.
   */
  showTagline?: boolean;
}) {
  return (
    <span className={cn('inline-flex items-center gap-2.5', className)}>
      <Image src="/disha-mark.svg" width={32} height={32} alt="" className="size-8" priority />
      <span>
        <span className="block text-base leading-none font-semibold tracking-tight">Disha</span>
        {showTagline && (
          <span className="text-muted-foreground mt-1 block text-[10px] leading-none">
            जो सवाल किसी ने नहीं पूछे
          </span>
        )}
      </span>
    </span>
  );
}
