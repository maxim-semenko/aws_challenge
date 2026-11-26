import { describe, expect, it } from 'vitest'
import { MISSING } from '../profile/format'
import { canSubmit, chatErrorMessage, chatMode, formatCell, shouldAutoSend } from './view'

describe('keyword / mode rule (spec 13 §Inputs)', () => {
  it('whole word "sql" in any case selects sql mode', () => {
    expect(chatMode('sql how many users')).toBe('sql')
    expect(chatMode('  SQL ')).toBe('sql')
    expect(chatMode('Sql: average weight')).toBe('sql')
    expect(chatMode('my sql question')).toBe('sql')
  })

  it('"sql" inside another word stays vector mode', () => {
    expect(chatMode('mysql users')).toBe('vector')
    expect(chatMode('sqlite')).toBe('vector')
    expect(chatMode('which users are similar to gender: female')).toBe('vector')
  })
})

describe('automatic request rule (spec 13 §Inputs)', () => {
  it('needs at least 3 trimmed characters', () => {
    expect(shouldAutoSend('ab', null)).toBe(false)
    expect(shouldAutoSend('  ab  ', null)).toBe(false)
    expect(shouldAutoSend('abc', null)).toBe(true)
  })

  it('never in sql mode', () => {
    expect(shouldAutoSend('sql', null)).toBe(false)
    expect(shouldAutoSend('sql how many users', null)).toBe(false)
    expect(shouldAutoSend('mysql users', null)).toBe(true)
  })

  it('not when equal to the last sent text', () => {
    expect(shouldAutoSend('female 1990 Poland ', 'female 1990 Poland')).toBe(false)
    expect(shouldAutoSend('female 1990 Poland', 'female 1990')).toBe(true)
  })

  it('Search / Enter accepts 1…500 trimmed characters in both modes', () => {
    expect(canSubmit('   ')).toBe(false)
    expect(canSubmit('a')).toBe(true)
    expect(canSubmit('sql count')).toBe(true)
    expect(canSubmit('x'.repeat(501))).toBe(false)
  })
})

describe('status → message (spec 13 §Outputs)', () => {
  it('maps every status of the spec', () => {
    expect(chatErrorMessage(400)).toBe('The question could not be answered. Rephrase it.')
    expect(chatErrorMessage(401)).toBeNull()
    expect(chatErrorMessage(403)).toBe('You do not have access to this page.')
    expect(chatErrorMessage(429)).toBe('The AI service is busy. Try again shortly.')
    expect(chatErrorMessage(502)).toBe('AI service not available — it is switched on only during working sessions.')
    expect(chatErrorMessage(500)).toBe('The search failed.')
    expect(chatErrorMessage(undefined)).toBe('The search failed.')
    expect(chatErrorMessage(503)).toBe('The search failed.')
  })
})

describe('cell formatting (spec 13 §Outputs)', () => {
  it('null, numbers, distance, booleans, strings', () => {
    expect(formatCell(null, 'country')).toBe(MISSING)
    expect(formatCell(170, 'heightCm')).toBe('170')
    expect(formatCell(72.5, 'avg')).toBe('72.5')
    expect(formatCell(0.123456, 'distance')).toBe('0.1235')
    expect(formatCell(0, 'distance')).toBe('0.0000')
    expect(formatCell(true, 'x')).toBe('true')
    expect(formatCell(false, 'x')).toBe('false')
    expect(formatCell('<b>Poland</b>', 'country')).toBe('<b>Poland</b>')
  })
})
