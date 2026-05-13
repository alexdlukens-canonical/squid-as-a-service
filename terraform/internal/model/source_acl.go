package model

type SourceACL struct {
	BaseResource
	CIDR []string `json:"cidr"`
}

type SourceACLInput struct {
	Name string   `json:"name"`
	CIDR []string `json:"cidr"`
}
