TEST?=./...
TIMEOUT?=120m

default:
	go build -o terraform-provider-terrasquid .

test:
	go test -v -count=1 -timeout=$(TIMEOUT) $(TEST)

testacc:
	TF_ACC=1 go test -v -count=1 -timeout=$(TIMEOUT) $(TEST)

lint:
	golangci-lint run ./...

fmt:
	gofmt -w .

vet:
	go vet ./...

tidy:
	go mod tidy
