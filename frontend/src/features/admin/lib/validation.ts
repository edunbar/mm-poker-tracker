export function isNumeric(v: unknown) {
  return v !== null && v !== "" && !Number.isNaN(Number(v));
}

export function formatErrorMessage(err: unknown): string {
  if (!err) return "An unknown error occurred.";
  
  // Handle axios error response
  if (typeof err === 'object' && err !== null) {
    const axiosError = err as any;
    
    // Try to get the error message from axios response data
    if (axiosError.response?.data?.error) {
      return axiosError.response.data.error;
    }
    
    // Try to get message from response data
    if (axiosError.response?.data?.message) {
      return axiosError.response.data.message;
    }
    
    // Try to get the message from the error object itself
    if (axiosError.message) {
      return axiosError.message;
    }
  }
  
  // Fallback to string conversion and try to extract quoted message
  const str = String(err);
  const quotedMatch = str.match(/"([^"]+)"/);
  if (quotedMatch?.[1]) {
    return quotedMatch[1];
  }
  
  // Return the string as-is if no patterns match
  return str;
}
