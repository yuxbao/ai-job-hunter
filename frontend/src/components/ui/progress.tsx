import * as React from "react";
import { cn } from "../../lib/utils";

type ProgressProps = React.HTMLAttributes<HTMLDivElement> & {
  value?: number;
};

const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(({ className, value = 0, ...props }, ref) => {
  const percent = Math.max(0, Math.min(100, value));

  return (
    <div className={cn("ui-progress", className)} ref={ref} {...props}>
      <div className="ui-progress-indicator" style={{ transform: `translateX(-${100 - percent}%)` }} />
    </div>
  );
});
Progress.displayName = "Progress";

export { Progress };
