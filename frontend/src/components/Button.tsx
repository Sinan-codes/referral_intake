import type { ButtonHTMLAttributes } from 'react'

export type ButtonVariant = 'neutral' | 'primary' | 'positive' | 'negative' | 'ghost'

const VARIANT_STYLES: Record<ButtonVariant, string> = {
  neutral: 'border border-slate-300 bg-white text-slate-700 hover:border-slate-400 hover:bg-slate-50',
  primary: 'border border-slate-900 bg-slate-900 text-white hover:bg-slate-800',
  positive: 'border border-emerald-600 bg-emerald-600 text-white hover:bg-emerald-700',
  negative: 'border border-red-600 bg-red-600 text-white hover:bg-red-700',
  ghost: 'border border-transparent text-slate-500 hover:bg-slate-100 hover:text-slate-700',
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
}

/** One button style for the whole app, so every clickable control lines up
 * on the same 36px height and shares the same radius/weight. */
export function Button({ variant = 'neutral', className = '', ...props }: ButtonProps) {
  return (
    <button
      type="button"
      className={`inline-flex h-9 items-center justify-center gap-1.5 whitespace-nowrap rounded-md px-3 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${VARIANT_STYLES[variant]} ${className}`}
      {...props}
    />
  )
}
