import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

// For purely decorative badges (e.g. status indicators with text nearby),
// add aria-hidden="true" at the usage site

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground shadow hover:bg-primary/80",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        // destructive: bg-[hsl(0,62.8%,30.6%)] ensures ≥4.5:1 contrast with white text
        // (light mode --destructive at 60.2% lightness gives ~3.5:1 which fails WCAG 1.4.3)
        destructive:
          "border-transparent bg-[hsl(0,62.8%,30.6%)] text-destructive-foreground shadow hover:bg-[hsl(0,62.8%,25%)]",
        outline: "text-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
