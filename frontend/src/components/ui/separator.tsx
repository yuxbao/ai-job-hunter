import * as React from "react";
import { cn } from "../../lib/utils";

type SeparatorProps = React.HTMLAttributes<HTMLDivElement> & {
  orientation?: "horizontal" | "vertical";
};

const Separator = React.forwardRef<HTMLDivElement, SeparatorProps>(
  ({ className, orientation = "horizontal", ...props }, ref) => (
    <div className={cn("ui-separator", `ui-separator-${orientation}`, className)} ref={ref} {...props} />
  ),
);
Separator.displayName = "Separator";

export { Separator };
