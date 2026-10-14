package scoring

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestHeadwayToLOS(t *testing.T) {
	grade, _ := HeadwayToLOS(8)
	assert.Equal(t, "A", grade)

	grade, _ = HeadwayToLOS(25)
	assert.Equal(t, "D", grade)

	grade, _ = HeadwayToLOS(120)
	assert.Equal(t, "F", grade)
}

func TestPTALGrade(t *testing.T) {
	assert.Equal(t, "1a", PTALGradeFromAI(1.0))
	assert.Equal(t, "3", PTALGradeFromAI(12.0))
	assert.Equal(t, "6b", PTALGradeFromAI(50.0))
}
