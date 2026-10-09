# D13 numerical boundary clarification

Herdr executor diagnostics found finite extreme historical z values when all valid prior same-month observations are exactly equal, caused by floating-point mean/variance roundoff. Examples include nightlight constant histories with spurious z near3e19. This is a computational zero-variance artifact, not justification for changing the approved source set or adding clipping.

D13 requires zero historical sample SD -> NA. Implement an exact constant-history check over the nonmissing prior same-month values (minimum == maximum when at least two values exist) so mathematically zero variance is reliably treated as zero even for decimal-valued histories. Keep strictly earlier years, ddof1 and z-before-MA. Do not apply an arbitrary epsilon, winsorization or clipping to genuinely nonconstant small-variance histories.

Add a small decimal-valued exact-constant example and a genuinely nonconstant nearby-value example to the feature checks. Preserve the frozen stress behavior independently. This clarifies numerical implementation of the already approved formula; it does not add a feature or experiment arm.
