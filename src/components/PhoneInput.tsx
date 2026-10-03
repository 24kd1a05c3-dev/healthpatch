import { getCountries, getCountryCallingCode, parsePhoneNumberFromString, type CountryCode } from 'libphonenumber-js/max'
import { inputClass } from './FormField'

export type PhoneDraft = { country: CountryCode; number: string }
export const emptyPhone = (): PhoneDraft => ({ country: 'IN', number: '' })
export function normalizePhone(value: PhoneDraft): string | null {
  if (!value.number.trim()) return null
  const parsed = parsePhoneNumberFromString(value.number.trim(), value.country)
  if (!parsed?.isValid() || parsed.ext) throw new Error('Enter a valid phone number with its area code. Extensions are not supported.')
  return parsed.number
}
const countries = getCountries()
const names = new Intl.DisplayNames(['en'], { type: 'region' })

export default function PhoneInput({ label, value, onChange }: { label: string; value: PhoneDraft; onChange: (value: PhoneDraft) => void }) {
  return <fieldset className="min-w-0"><legend className="text-sm font-medium text-[#334155]">{label}</legend>
    <div className="grid grid-cols-[minmax(0,140px)_minmax(0,1fr)] gap-2">
      <select aria-label={`${label} country code`} className={inputClass} value={value.country} onChange={e => onChange({ ...value, country: e.target.value as CountryCode })}>
        {countries.map(country => <option key={country} value={country}>{names.of(country)} +{getCountryCallingCode(country)}</option>)}
      </select>
      <input aria-label={label} type="tel" autoComplete="tel-national" inputMode="tel" maxLength={40} value={value.number} onChange={e => onChange({ ...value, number: e.target.value })} className={inputClass} />
    </div>
  </fieldset>
}
