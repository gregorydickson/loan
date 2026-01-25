/**
 * Shared formatting utilities for consistent UI display.
 */

/**
 * Determines the badge variant based on confidence score.
 *
 * Used to provide visual feedback on extraction confidence:
 * - >= 0.7 (70%+): "default" - success/green, high confidence
 * - >= 0.5 (50-69%): "secondary" - warning/yellow, medium confidence
 * - < 0.5 (0-49%): "destructive" - error/red, low confidence
 *
 * @param score - Confidence score between 0 and 1
 * @returns Badge variant for the shadcn Badge component
 */
export function getConfidenceBadgeVariant(
  score: number
): "default" | "secondary" | "destructive" {
  if (score >= 0.7) return "default";
  if (score >= 0.5) return "secondary";
  return "destructive";
}
