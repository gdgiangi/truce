import { cn } from '../lib/utils'

describe('cn utility function', () => {
  it('merges class names correctly', () => {
    expect(cn('class1', 'class2')).toBe('class1 class2')
  })

  it('handles conditional classes', () => {
    expect(cn('class1', true && 'class2', false && 'class3')).toBe('class1 class2')
  })

  it('handles undefined and null values', () => {
    expect(cn('class1', undefined, null, 'class2')).toBe('class1 class2')
  })

  it('merges Tailwind classes correctly (removes duplicates)', () => {
    // This tests the twMerge functionality
    expect(cn('px-2 py-1', 'px-3')).toBe('py-1 px-3')
  })

  it('handles empty input', () => {
    expect(cn()).toBe('')
  })

  it('handles arrays of classes', () => {
    expect(cn(['class1', 'class2'], 'class3')).toBe('class1 class2 class3')
  })
})
