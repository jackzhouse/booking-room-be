# Employee synchronization

`POST /api/v1/admin/users/sync-employees` creates an asynchronous employee-sync task. Admin clients poll `GET /api/v1/admin/tasks/{task_id}` until `status` is `completed` or `failed`.

The directory client requests every employee page. It uses source pagination metadata when supplied, otherwise continues until the source returns an empty page. Repeated pages stop the fallback safely, so a non-paginated source cannot loop forever.

## Task response

```json
{
  "task_id": "...",
  "status": "processing",
  "progress": 65,
  "message": "Mengambil employee halaman 2 dari 3",
  "metadata": {
    "division_count": 8,
    "employee_page": 2,
    "employee_total_pages": 3,
    "employee_fetched": 154
  }
}
```

Completed tasks add `employee_count`, `fetched`, `processed`, `created`, `updated`, and `skipped`. Failed tasks expose only safe diagnostic fields: `error_type`, external `endpoint`, and external `status_code` when available. Tokens are never returned.
