
import pytest
from pydantic import ValidationError as PydanticError

from adit.spec import DftbMethod, Task
from adit.validate_types import friendly_pydantic


def test_method_type_error_is_named_by_field():
    with pytest.raises(PydanticError) as ex:
        DftbMethod(sk_set="mio-1-1", scc_tolerance="abc")
    text = friendly_pydantic(ex.value)
    assert not text.lower().startswith("1 validation error")
    assert text.splitlines()[0].startswith("scc_tolerance:")


def test_task_type_error_uses_group_label():
    with pytest.raises(PydanticError) as ex:
        Task(type="no_such_task")
    assert friendly_pydantic(ex.value).splitlines()[0].startswith("計算の種類:")
