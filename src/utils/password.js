// Strength meter is advisory; validation must enforce every requirement.
export const validPassword = (pw = '') => pw.length >= 8 && /[A-Z]/.test(pw) && /[a-z]/.test(pw) && /\d/.test(pw);
