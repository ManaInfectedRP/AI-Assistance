import { expect, test } from '@playwright/test'

test('user can type a message and see it appear', async ({ page }) => {
  await page.goto('/')
  const input = page.getByTestId('input-bar')
  await input.fill('Hello from e2e test')
  await input.press('Enter')
  await expect(page.getByTestId('message-list')).toContainText('Hello from e2e test')
})

test('assistant response appears after sending a message', async ({ page }) => {
  await page.goto('/')
  await page.getByTestId('input-bar').fill('Say hi')
  await page.getByTestId('input-bar').press('Enter')
  // Wait up to 30s for the assistant to respond (Ollama can be slow)
  await expect(page.getByTestId('assistant-message')).not.toBeEmpty({ timeout: 30000 })
})
