package model

type ACLRule struct {
	BaseResource
	Priority  int     `json:"priority"`
	Src       *string `json:"src,omitempty"`
	SrcGroup  *string `json:"src_group,omitempty"`
	Dst       *string `json:"dst,omitempty"`
	DstGroup  *string `json:"dst_group,omitempty"`
}

type ACLRuleInput struct {
	Priority  int     `json:"priority"`
	Src       *string `json:"src,omitempty"`
	SrcGroup  *string `json:"src_group,omitempty"`
	Dst       *string `json:"dst,omitempty"`
	DstGroup  *string `json:"dst_group,omitempty"`
}
