import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ModelSelector } from './ModelSelector'

describe('ModelSelector', () => {
  it('renders with the given value', () => {
    render(<ModelSelector value="chat" onChange={vi.fn()} />)
    expect(screen.getByRole('combobox')).toHaveValue('chat')
  })

  it('calls onChange when a different model is selected', () => {
    const onChange = vi.fn()
    render(<ModelSelector value="chat" onChange={onChange} />)
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'code' } })
    expect(onChange).toHaveBeenCalledWith('code')
  })

  it('is disabled when disabled prop is true', () => {
    render(<ModelSelector value="chat" onChange={vi.fn()} disabled />)
    expect(screen.getByRole('combobox')).toBeDisabled()
  })
})
