import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { useRouter } from 'next/navigation'
import { SearchBar } from '@/components/search-bar'

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}))

// Mock fetch
global.fetch = jest.fn()

const mockPush = jest.fn()

beforeEach(() => {
  (useRouter as jest.Mock).mockReturnValue({
    push: mockPush,
  })
  mockPush.mockClear()
    ; (fetch as jest.Mock).mockClear()
})

describe('SearchBar', () => {
  it('renders with default placeholder', () => {
    render(<SearchBar />)
    expect(screen.getByPlaceholderText('Search claims and evidence')).toBeInTheDocument()
  })

  it('renders with custom placeholder', () => {
    render(<SearchBar placeholder="Custom placeholder" />)
    expect(screen.getByPlaceholderText('Custom placeholder')).toBeInTheDocument()
  })

  it('renders with initial query', () => {
    render(<SearchBar initialQuery="test query" />)
    expect(screen.getByDisplayValue('test query')).toBeInTheDocument()
  })

  it('updates query on input change', () => {
    render(<SearchBar />)
    const input = screen.getByRole('textbox')

    fireEvent.change(input, { target: { value: 'new search term' } })
    expect(input).toHaveValue('new search term')
  })

  it('navigates to analyzing page on form submit', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ session_id: 'test-session-123' })
    })

    render(<SearchBar />)
    const input = screen.getByRole('textbox')
    const form = input.closest('form')

    fireEvent.change(input, { target: { value: 'test search' } })
    fireEvent.submit(form!)

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/analyzing?session=test-session-123&q=test%20search')
    })
  })

  it('does not navigate when query is empty', async () => {
    render(<SearchBar />)
    const input = screen.getByRole('textbox')
    const form = input.closest('form')

    fireEvent.submit(form!)

    expect(mockPush).not.toHaveBeenCalled()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('trims whitespace from query before navigation', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ session_id: 'test-session-123' })
    })

    render(<SearchBar />)
    const input = screen.getByRole('textbox')
    const form = input.closest('form')

    fireEvent.change(input, { target: { value: '  test search  ' } })
    fireEvent.submit(form!)

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/analyzing?session=test-session-123&q=test%20search')
    })
  })

  it('updates query when initialQuery prop changes', () => {
    const { rerender } = render(<SearchBar initialQuery="initial" />)
    expect(screen.getByDisplayValue('initial')).toBeInTheDocument()

    rerender(<SearchBar initialQuery="updated" />)
    expect(screen.getByDisplayValue('updated')).toBeInTheDocument()
  })
})
