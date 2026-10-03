import { useId, type InputHTMLAttributes } from 'react'

export const inputClass = 'mt-1 w-full min-w-0 rounded-md border border-[#CBD5E1] bg-white px-3 py-2.5 text-sm text-[#0F172A] focus:border-[#0D9488] focus:ring-2 focus:ring-[#CCFBF1]'

// Stable component identity preserves focus and selection across form updates.
export default function FormField({ label, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  const id = useId()
  return <label htmlFor={id} className="block text-sm font-medium text-[#334155]">{label}<input {...props} id={id} className={inputClass} /></label>
}
