import os
import sys
import dotenv

os.chdir(r"A:\ZB\git_repo\waditu\czsc\examples\test_offline")
sys.path.insert(0, r"A:\ZB\git_repo\waditu\czsc")
dotenv.load_dotenv(dotenv.find_dotenv(raise_error_if_not_found=True), override=True)
from czsc.fsa import BiTable

bi_table = BiTable(app_token="ZkWzbY7xjaicgkslpdUc1tQLnk8")

print(
    bi_table.create_table(
        name="test2",
        default_view_name="视图1",
        fields=[{"field_name": "text", "type": 1}, {"field_name": "text1", "type": 2}],
    )
)
print(bi_table.batch_create_table(["tb1", "tb2", "tb3"]))
print(bi_table.delete_table("tblNW6s4ldB3dhCG"))
print(bi_table.batch_delete_table(["tbly1sheIukE622s", "tblNK7XcwQDLdomG"]))
print(bi_table.patch_table("tblzRoIFq3URau2V", "name_patch"))
print(bi_table.list_tables(page_token="tbltFoOtwXCuhtj9"))

print(bi_table.table_record_get(table_id="tblfSD2jLnUMi4sE", record_id="recwyiPrHM"))
print(bi_table.table_record_search(table_id="tblfSD2jLnUMi4sE"))
print(bi_table.table_record_create(table_id="tblfSD2jLnUMi4sE", fields={"文本": "多行文本内容", "日期": 1674206443000}))

print(
    bi_table.table_record_update(
        table_id="tblfSD2jLnUMi4sE",
        record_id="recuhm4cMqw7fn",
        fields={
            "文本": "多行文本内容修改",
        },
    )
)
print(bi_table.table_record_delete(table_id="tblfSD2jLnUMi4sE", record_id="recwyiPrHM"))

print(
    bi_table.table_record_batch_create(
        table_id="tblfSD2jLnUMi4sE",
        fields=[{"文本": "多行文本内容1"}, {"文本": "多行文本内容2"}, {"文本": "多行文本内容3", "日期": 1674206443000}],
    )
)

print(
    bi_table.table_record_batch_update(
        table_id="tblfSD2jLnUMi4sE",
        records=[
            {"record_id": "recuhm9s2axNVM", "fields": {"文本": "批量修改内容1"}},
            {"record_id": "recuhm9s2aZ3At", "fields": {"文本": "批量修改内容2"}},
        ],
    )
)

print(bi_table.table_record_batch_delete(table_id="tblfSD2jLnUMi4sE", record_ids=["recuhm9s2axNVM", "recuhm9s2aZ3At"]))

print(bi_table.table_view_list(table_id="tblfSD2jLnUMi4sE"))
print(bi_table.table_field_list(table_id="tblfSD2jLnUMi4sE", view_id="vewo15a8k6"))

print(bi_table.table_view_patch(table_id="tblfSD2jLnUMi4sE", view_id="vewo15a8k6", infos={"view_name": "修改的视图名"}))

print(bi_table.table_view_get(table_id="tblfSD2jLnUMi4sE", view_id="vewo15a8k6"))

print(bi_table.table_view_create(table_id="tblfSD2jLnUMi4sE", view_name="测试添加视图", view_type="grid"))
print(bi_table.table_view_delete(table_id="tblfSD2jLnUMi4sE", view_id="vew4hoglsH"))

print(
    bi_table.table_field_create(
        table_id="tblfSD2jLnUMi4sE", field_name="测试添加2", type=1, description={"text": "测试的"}
    )
)
print(
    bi_table.table_field_update(
        table_id="tblfSD2jLnUMi4sE",
        field_id="fldEbAErbT",
        field_name="测试添加2修改",
        type=11,
        description={"text": "测试的 并修改"},
        property={"multiple": True},
    )
)

print(bi_table.table_field_delete(table_id="tblfSD2jLnUMi4sE", field_id="fldEbAErbT"))

print(bi_table.table_form_list(table_id="tblfSD2jLnUMi4sE", form_id="vewafwFMhM"))
print(
    bi_table.table_form_patch(
        table_id="tblfSD2jLnUMi4sE", form_id="vewafwFMhM", name="测试修改的名字", description="测试修改的备注"
    )
)
print(bi_table.table_form_get(table_id="tblfSD2jLnUMi4sE", form_id="vewafwFMhM"))
print(
    bi_table.table_form_patch(
        table_id="tblfSD2jLnUMi4sE",
        form_id="vewafwFMhM",
        field_id="fld7mfWuZ2",
        title="修改的title",
        description="api修改的",
    )
)

print(bi_table.table_copy(name="测试添加的"))
print(bi_table.table_create(name="测试添加的"))
print(bi_table.table_get(app_token="YuSZbIPLlaPenUsOzbfcL25Sn4g"))
print(bi_table.table_update(app_token="YuSZbIPLlaPenUsOzbfcL25Sn4g", name="修改成的新名字"))
