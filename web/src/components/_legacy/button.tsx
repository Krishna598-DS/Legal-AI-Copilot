import { cn } from "@/lib/cn";
import { ButtonHTMLAttributes, forwardRef } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost" | "danger" | "outline";
  size?: "sm" | "md";
};

export const Button = forwardRef<HTMLButtonElement, Props>(
  ({ className, variant = "outline", size = "md", ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center rounded-lg font-medium transition disabled:opacity-50 disabled:cursor-not-allowed",
        size === "sm" ? "px-3 py-1.5 text-sm" : "px-4 py-2 text-sm",
        variant === "primary" &&
          "bg-teal-500 text-teal-950 border border-transparent hover:bg-teal-400",
        variant === "ghost" &&
          "bg-transparent border border-transparent text-slate-200 hover:bg-slate-800",
        variant === "outline" &&
          "bg-slate-800 border border-slate-600 text-slate-100 hover:border-teal-500",
        variant === "danger" && "bg-transparent text-red-300 hover:bg-red-950/40",
        className
      )}
      {...props}
    />
  )
);
Button.displayName = "Button";
