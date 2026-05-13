package client

import (
	"errors"
	"testing"
)

func TestAPIError_ErrorWithoutFieldErrors(t *testing.T) {
	err := &APIError{
		StatusCode: 404,
		ErrType:    "not_found",
		Message:    "resource not found",
	}
	want := "API error 404: resource not found (error=not_found)"
	if got := err.Error(); got != want {
		t.Errorf("Error() = %q, want %q", got, want)
	}
}

func TestAPIError_ErrorWithFieldErrors(t *testing.T) {
	err := &APIError{
		StatusCode:  400,
		ErrType:     "validation_error",
		Message:     "validation failed",
		FieldErrors: map[string]string{"name": "required"},
	}
	want := "API error 400: validation failed (error=validation_error, field_errors=map[name:required])"
	if got := err.Error(); got != want {
		t.Errorf("Error() = %q, want %q", got, want)
	}
}

func TestIsNotFoundError_True(t *testing.T) {
	err := &APIError{StatusCode: 404}
	if !IsNotFoundError(err) {
		t.Error("IsNotFoundError = false, want true")
	}
}

func TestIsNotFoundError_FalseStatus(t *testing.T) {
	err := &APIError{StatusCode: 500}
	if IsNotFoundError(err) {
		t.Error("IsNotFoundError = true, want false")
	}
}

func TestIsNotFoundError_Nil(t *testing.T) {
	if IsNotFoundError(nil) {
		t.Error("IsNotFoundError = true, want false")
	}
}

func TestIsNotFoundError_OtherErrorType(t *testing.T) {
	err := errors.New("not found")
	if IsNotFoundError(err) {
		t.Error("IsNotFoundError = true, want false")
	}
}

func TestIsUnauthorizedError_401(t *testing.T) {
	err := &APIError{StatusCode: 401}
	if !IsUnauthorizedError(err) {
		t.Error("IsUnauthorizedError = false, want true")
	}
}

func TestIsUnauthorizedError_403(t *testing.T) {
	err := &APIError{StatusCode: 403}
	if !IsUnauthorizedError(err) {
		t.Error("IsUnauthorizedError = false, want true")
	}
}

func TestIsUnauthorizedError_FalseStatus(t *testing.T) {
	err := &APIError{StatusCode: 404}
	if IsUnauthorizedError(err) {
		t.Error("IsUnauthorizedError = true, want false")
	}
}

func TestIsUnauthorizedError_Nil(t *testing.T) {
	if IsUnauthorizedError(nil) {
		t.Error("IsUnauthorizedError = true, want false")
	}
}

func TestIsUnauthorizedError_OtherErrorType(t *testing.T) {
	err := errors.New("unauthorized")
	if IsUnauthorizedError(err) {
		t.Error("IsUnauthorizedError = true, want false")
	}
}
