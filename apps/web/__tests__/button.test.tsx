import { render, screen } from '@testing-library/react'
import { Button } from '@/components/ui/button'

describe('Button component', () => {
  it('renders button with default variant and size', () => {
    render(<Button>Click me</Button>)
    const button = screen.getByRole('button', { name: /click me/i })
    expect(button).toBeInTheDocument()
    expect(button).toHaveClass('h-11', 'px-6', 'py-2') // default size classes
  })

  it('renders button with custom variant', () => {
    render(<Button variant="destructive">Delete</Button>)
    const button = screen.getByRole('button', { name: /delete/i })
    expect(button).toBeInTheDocument()
    expect(button).toHaveClass('bg-destructive')
  })

  it('renders button with custom size', () => {
    render(<Button size="sm">Small button</Button>)
    const button = screen.getByRole('button', { name: /small button/i })
    expect(button).toBeInTheDocument()
    expect(button).toHaveClass('h-9', 'px-4', 'text-xs')
  })

  it('renders button with outline variant', () => {
    render(<Button variant="outline">Outline button</Button>)
    const button = screen.getByRole('button', { name: /outline button/i })
    expect(button).toBeInTheDocument()
    expect(button).toHaveClass('border', 'border-border')
  })

  it('handles disabled state', () => {
    render(<Button disabled>Disabled button</Button>)
    const button = screen.getByRole('button', { name: /disabled button/i })
    expect(button).toBeInTheDocument()
    expect(button).toBeDisabled()
    expect(button).toHaveClass('disabled:opacity-50')
  })

  it('applies custom className', () => {
    render(<Button className="custom-class">Custom button</Button>)
    const button = screen.getByRole('button', { name: /custom button/i })
    expect(button).toBeInTheDocument()
    expect(button).toHaveClass('custom-class')
  })

  it('forwards onClick handler', () => {
    const handleClick = jest.fn()
    render(<Button onClick={handleClick}>Clickable button</Button>)
    const button = screen.getByRole('button', { name: /clickable button/i })
    
    button.click()
    expect(handleClick).toHaveBeenCalledTimes(1)
  })
})
