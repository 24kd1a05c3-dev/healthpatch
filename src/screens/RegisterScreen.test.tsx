// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import RegisterScreen from './RegisterScreen'

const { register } = vi.hoisted(() => ({ register: vi.fn().mockResolvedValue(undefined) }))
vi.mock('../context/AuthContext', () => ({ useAuth: () => ({ register }) }))
afterEach(() => { cleanup(); register.mockClear() })

describe('patient registration', () => {
  it('keeps the same focused input while typing and preserves values across steps', async () => {
    const user = userEvent.setup()
    render(<RegisterScreen onNavigate={vi.fn()} />)
    const first = screen.getByLabelText('First name') as HTMLInputElement
    await user.type(first, 'Anirudh')
    expect(first.value).toBe('Anirudh')
    expect(document.activeElement).toBe(first)
    expect(screen.getByLabelText('First name')).toBe(first)
    await user.type(screen.getByLabelText('Last name'), 'Test')
    await user.type(screen.getByLabelText('Phone number', { exact: true }), '9876543210')
    expect((screen.getByLabelText('Phone number country code') as HTMLSelectElement).value).toBe('IN')
    await user.click(screen.getByRole('button', { name: 'Continue' }))
    await user.type(screen.getByLabelText('Contact name'), 'Test Contact')
    await user.type(screen.getByLabelText('Emergency phone number', { exact: true }), '01123456789')
    await user.click(screen.getByRole('button', { name: 'Back' }))
    expect((screen.getByLabelText('First name') as HTMLInputElement).value).toBe('Anirudh')
    expect((screen.getByLabelText('Phone number', { exact: true }) as HTMLInputElement).value).toBe('9876543210')
    await user.click(screen.getByRole('button', { name: 'Continue' }))
    await user.click(screen.getByRole('button', { name: 'Continue' }))
    await user.click(screen.getByLabelText('Asthma'))
    await user.type(screen.getByLabelText('Allergies (comma separated)'), 'Latex')
    await user.click(screen.getByRole('button', { name: 'Continue' }))
    await user.type(screen.getByLabelText('Email address'), 'test@example.com')
    await user.type(screen.getByLabelText('Password', { exact: true }), 'LongPassword123!')
    await user.type(screen.getByLabelText('Confirm password'), 'LongPassword123!')
    await user.click(screen.getByRole('button', { name: 'Create account' }))
    expect(register).toHaveBeenCalledWith(expect.objectContaining({ phone: '+919876543210', emergency_contact_phone: '+911123456789', emergency_contact_name: 'Test Contact', medical_conditions: ['Asthma'], allergies: ['Latex'] }))
  })

  it('rejects an invalid phone number without advancing the form', async () => {
    const user = userEvent.setup()
    render(<RegisterScreen onNavigate={vi.fn()} />)
    await user.type(screen.getByLabelText('First name'), 'Test')
    await user.type(screen.getByLabelText('Last name'), 'Person')
    await user.type(screen.getByLabelText('Phone number', { exact: true }), '123')
    await user.click(screen.getByRole('button', { name: 'Continue' }))
    expect(screen.getByRole('alert').textContent).toContain('valid phone number')
    expect(register).not.toHaveBeenCalled()
  })
})
