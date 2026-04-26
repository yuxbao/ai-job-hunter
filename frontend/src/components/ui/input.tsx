import * as React from "react";
import { cn } from "../../lib/utils";

const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => <input className={cn("ui-input", className)} ref={ref} {...props} />,
);
Input.displayName = "Input";

export { Input };
