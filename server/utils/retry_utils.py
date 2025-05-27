import time
import random
from typing import Callable, Any, Optional, Type, Union, Tuple
from functools import wraps
import logging

from ..config.settings import settings

# Set up logging
logger = logging.getLogger(__name__)

class RetryableError(Exception):
    """Base class for errors that should trigger a retry."""
    pass

class APIConnectionError(RetryableError):
    """Error for API connection issues."""
    pass

def is_retryable_error(error: Exception) -> bool:
    """Determine if an error should trigger a retry."""
    error_str = str(error).lower()
    error_type = type(error).__name__.lower()
    
    # Check for connection-related errors
    connection_indicators = [
        'connection error',
        'connection timeout',
        'timeout',
        'server disconnected',
        'remote protocol error',
        'connection reset',
        'network error',
        'api connection error',
        'rate limit',
        'too many requests',
        'service unavailable',
        'internal server error',
        'bad gateway',
        'gateway timeout'
    ]
    
    # Check error message
    for indicator in connection_indicators:
        if indicator in error_str:
            return True
    
    # Check error type
    retryable_types = [
        'connectionerror',
        'timeout',
        'apiconnectionerror',
        'httpxremoteprotocolerror',
        'remoteprotocolerror',
        'modelproviderror'  # From agno library
    ]
    
    for retryable_type in retryable_types:
        if retryable_type in error_type:
            return True
    
    return False

def calculate_delay(attempt: int, base_delay: float = None, backoff_factor: float = None, max_delay: float = None) -> float:
    """Calculate delay for exponential backoff with jitter."""
    base_delay = base_delay or settings.RETRY_DELAY
    backoff_factor = backoff_factor or settings.RETRY_BACKOFF_FACTOR
    max_delay = max_delay or settings.MAX_RETRY_DELAY
    
    # Exponential backoff: base_delay * (backoff_factor ^ attempt)
    delay = base_delay * (backoff_factor ** attempt)
    
    # Cap at max_delay
    delay = min(delay, max_delay)
    
    # Add jitter (±25% of the delay)
    jitter = delay * 0.25 * (2 * random.random() - 1)
    delay = max(0, delay + jitter)
    
    return delay

def retry_with_backoff(
    max_retries: int = None,
    base_delay: float = None,
    backoff_factor: float = None,
    max_delay: float = None,
    retryable_exceptions: Tuple[Type[Exception], ...] = None
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay on each retry
        max_delay: Maximum delay between retries
        retryable_exceptions: Tuple of exception types that should trigger retries
    """
    max_retries = max_retries or settings.MAX_RETRIES
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):  # +1 for initial attempt
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # Check if this is the last attempt
                    if attempt >= max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries. Last error: {e}")
                        raise e
                    
                    # Check if error is retryable
                    should_retry = False
                    if retryable_exceptions:
                        should_retry = isinstance(e, retryable_exceptions)
                    else:
                        should_retry = is_retryable_error(e)
                    
                    if not should_retry:
                        logger.error(f"Function {func.__name__} failed with non-retryable error: {e}")
                        raise e
                    
                    # Calculate delay and wait
                    delay = calculate_delay(attempt, base_delay, backoff_factor, max_delay)
                    logger.warning(f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
            
            # This should never be reached, but just in case
            raise last_exception
        
        return wrapper
    return decorator

def retry_api_call(
    func: Callable,
    *args,
    max_retries: int = None,
    base_delay: float = None,
    backoff_factor: float = None,
    max_delay: float = None,
    **kwargs
) -> Any:
    """
    Retry an API call with exponential backoff.
    
    Args:
        func: Function to retry
        *args: Arguments to pass to the function
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay on each retry
        max_delay: Maximum delay between retries
        **kwargs: Keyword arguments to pass to the function
    
    Returns:
        Result of the function call
    
    Raises:
        The last exception if all retries fail
    """
    max_retries = max_retries or settings.MAX_RETRIES
    last_exception = None
    
    for attempt in range(max_retries + 1):  # +1 for initial attempt
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            
            # Check if this is the last attempt
            if attempt >= max_retries:
                logger.error(f"API call {func.__name__} failed after {max_retries} retries. Last error: {e}")
                raise e
            
            # Check if error is retryable
            if not is_retryable_error(e):
                logger.error(f"API call {func.__name__} failed with non-retryable error: {e}")
                raise e
            
            # Calculate delay and wait
            delay = calculate_delay(attempt, base_delay, backoff_factor, max_delay)
            logger.warning(f"API call {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying in {delay:.2f} seconds...")
            time.sleep(delay)
    
    # This should never be reached, but just in case
    raise last_exception 