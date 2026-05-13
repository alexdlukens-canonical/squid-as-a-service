package client

import "fmt"

type APIError struct {
	StatusCode  int               `json:"-"`
	ErrType     string            `json:"error"`
	Message     string            `json:"message"`
	FieldErrors map[string]string `json:"field_errors"`
}

func (e *APIError) Error() string {
	if e.FieldErrors != nil {
		return fmt.Sprintf("API error %d: %s (error=%s, field_errors=%v)", e.StatusCode, e.Message, e.ErrType, e.FieldErrors)
	}
	return fmt.Sprintf("API error %d: %s (error=%s)", e.StatusCode, e.Message, e.ErrType)
}

func IsNotFoundError(err error) bool {
	if apiErr, ok := err.(*APIError); ok {
		return apiErr.StatusCode == 404
	}
	return false
}

func IsUnauthorizedError(err error) bool {
	if apiErr, ok := err.(*APIError); ok {
		return apiErr.StatusCode == 401 || apiErr.StatusCode == 403
	}
	return false
}
