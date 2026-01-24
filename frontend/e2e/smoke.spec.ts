import { test, expect } from '@playwright/test';

test.describe('Dashboard Smoke Tests', () => {
  test('dashboard loads successfully', async ({ page }) => {
    await page.goto('/');

    // Verify page loads without crashing
    await expect(page).toHaveTitle(/Loan/i);

    // Verify main content area is visible
    await expect(page.locator('main')).toBeVisible();
  });

  test('navigation sidebar is visible', async ({ page }) => {
    await page.goto('/');

    // Verify sidebar navigation exists
    const sidebar = page.locator('aside, nav, [role="navigation"]');
    await expect(sidebar.first()).toBeVisible();
  });

  test('borrowers page loads', async ({ page }) => {
    await page.goto('/borrowers');

    // Should show borrowers content or empty state
    await expect(
      page.getByText(/borrower/i).or(page.getByText(/no data/i))
    ).toBeVisible();
  });
});

test.describe('Document Upload Smoke Tests', () => {
  test('documents page accessible', async ({ page }) => {
    await page.goto('/documents');

    // Verify page loads
    await expect(page.locator('main')).toBeVisible();
  });

  test('upload area is present on documents page', async ({ page }) => {
    await page.goto('/documents');

    // Look for file input or upload-related UI elements
    const uploadArea = page
      .locator('input[type="file"]')
      .or(page.getByText(/upload/i))
      .or(page.getByText(/drag.*drop/i));

    await expect(uploadArea.first()).toBeVisible();
  });

  test('file input is functional', async ({ page }) => {
    await page.goto('/documents');

    // Find file input
    const fileInput = page.locator('input[type="file"]');
    if ((await fileInput.count()) > 0) {
      await expect(fileInput.first()).toBeEnabled();
    }
  });
});

test.describe('API Integration Smoke Tests', () => {
  test('documents list loads from API', async ({ page }) => {
    await page.goto('/documents');

    // Wait for page to finish loading (API call to complete)
    await page.waitForLoadState('networkidle');

    // Page should render without error
    await expect(page.locator('main')).toBeVisible();
  });

  test('borrowers list loads from API', async ({ page }) => {
    await page.goto('/borrowers');

    // Wait for API response
    await page.waitForLoadState('networkidle');

    // Page should render without error
    await expect(page.locator('main')).toBeVisible();
  });
});

test.describe('Navigation Smoke Tests', () => {
  test('can navigate between pages', async ({ page }) => {
    await page.goto('/');

    // Navigate to documents
    const docsLink = page.getByRole('link', { name: /document/i });
    if ((await docsLink.count()) > 0) {
      await docsLink.first().click();
      await expect(page).toHaveURL(/document/i);
    }

    // Navigate to borrowers
    const borrowersLink = page.getByRole('link', { name: /borrower/i });
    if ((await borrowersLink.count()) > 0) {
      await borrowersLink.first().click();
      await expect(page).toHaveURL(/borrower/i);
    }
  });

  test('dashboard link returns to home', async ({ page }) => {
    await page.goto('/documents');

    // Click dashboard/home link
    const homeLink = page
      .getByRole('link', { name: /dashboard/i })
      .or(page.getByRole('link', { name: /home/i }));

    if ((await homeLink.count()) > 0) {
      await homeLink.first().click();
      await expect(page).toHaveURL('/');
    }
  });
});
