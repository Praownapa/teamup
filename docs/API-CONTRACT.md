# Frontend API contract

Reviewed against `src/api/endpoints.js`, `src/api/mock.js` and page consumers on 2026-10-30 (Asia/Bangkok). No backend implementation was supplied. This is the existing frontend contract to implement/verify, not a claim that the backend already conforms.

Paths below are relative to `config.apiBaseUrl` (default `/api`). Thus `/admin/overview` means `/api/admin/overview`; `/api/admin/stats` is obsolete documentation, not an alias to implement. Vite's proxy and the supplied ALB design preserve `/api`; configure FastAPI routes/root routing accordingly. Do not add `/api` twice.

| Method | Relative path | Frontend function | Payload / response |
|---|---|---|---|
| GET | /users/me | getMe | Current profile |
| PUT | /users/me | updateMe | Profile fields; returns full profile |
| GET | /users/{id} | getUser | Public student profile |
| GET | /users/me/counts | getCounts | pending_requests, unread_notifications |
| GET | /users/me/dashboard | getDashboard | stats, recommended, my_teams, activity |
| GET | /projects | listProjects | q, categories, skills, role, recruiting, spots, sort query; array |
| GET | /projects/filters | listFilterOptions | categories [{name,count}], roles [string] |
| GET | /projects/{id} | getProject / getTeam | Full project view including members |
| POST | /projects | createProject | Project form; returns full project view |
| PATCH | /projects/{id} | updateProject | Project fields; returns full project view |
| POST | /projects/{id}/save | toggleSave | Returns {saved:boolean} |
| POST | /projects/{id}/reports | reportProject | {reason}; returns {ok:true} |
| POST | /projects/{id}/requests | requestToJoin | {role,message}; returns full project view |
| GET | /projects/{id}/recommendations | getRecommendedStudents | Array of recommended students |
| POST | /projects/{id}/invitations | inviteStudent | {user_id,role}; returns {ok:true} |
| PATCH | /projects/{id}/members/{userId} | changeMemberRole | {role}; returns full project view |
| DELETE | /projects/{id}/members/{userId} | removeMember | Returns full project view (not 204) |
| DELETE | /projects/{id}/members/me | leaveTeam | 204 / no body |
| GET | /requests | listRequests | Array of requests / invitations |
| PATCH | /requests/{id} | respondRequest | {status:accepted / rejected}; returns request view |
| DELETE | /requests/{id} | cancelRequest | 204 / no body |
| GET | /notifications | listNotifications | Array of notifications |
| POST | /notifications/{id}/read | markRead | 204 / no body |
| POST | /notifications/read-all | markAllRead | 204 / no body |
| POST | /uploads/presign | getUploadUrl | {filename,content_type}; {upload_url,file_url} |
| GET | /admin/overview | adminOverview | period=7d / 30d / semester; overview object |
| PATCH | /admin/reports/{id} | adminResolveReport | {status:removed / dismissed}; 204 |
| PATCH | /admin/users/{id} | adminSetUserStatus | {status:suspended / active}; 204 |
| POST | /admin/categories | adminAddCategory | {name}; 204 |
| DELETE | /admin/categories/{name} | adminDeleteCategory | URL-encoded name; 204 |

## Response rules

- Collections are arrays, not `{items:...}` envelopes. Do not paginate without coordinating UI changes.
- Successful responses must contain JSON except status 204. In particular `removeMember` and `changeMemberRole` return a full project, because Team Management immediately renders that response.
- Error JSON: prefer `{ "message": "Readable message" }`. `{ "detail": "Readable message" }` and FastAPI validation `detail: [{loc:[...],msg:"..."}]` also work. `message` takes precedence. Non-JSON failures fall back to status text / status number. Status 401 redirects to `/login`; 403 stays on the page and shows the message.
- Requests attach a Cognito **access token**, when available, as `Authorization: Bearer ...`. Server must reject missing/invalid tokens, validate issuer, signature, expiry, token_use and app client, and derive user identity from verified `sub`. Do not expect email or custom profile attributes in the access token; choose a trusted backend bootstrap/sync strategy.
- Numeric IDs are used by the current mock and `FindTeammates` converts project query values to Number. Coordinate before switching to UUID IDs.
- Filter `categories` and `skills` are comma-separated strings. `recruiting` and `spots` use string `true`. Sort values: `match`, `newest`, `spots`.

## Shapes consumed by pages

Use `src/api/mock.js` view builders and `docs/RESPONSE-EXAMPLES.json` for concrete examples; examples are synthetic mock output, not production records or a server implementation.

- Profile: id, name, email, student_id, major, year, role, status, bio, portfolio, open_to_projects, skills [{name,level}], interests [string], notify {invitations,requests,team,digest}, teams [{id,title,is_owner,status}], stats {teams,projects,skills}. `PUT /users/me` currently sends subsets; preserve omitted fields despite the PUT verb. No API verb was changed in this review.
- Project: id, title, category, course, description, cover_url, owner {id,name,major,year}, max_size, accepting, status, created_at, duration, meeting, deadline, saved, skills [[name,matchedBoolean]], match, roles [{name,user:null|studentBrief}], members [{id,name,major,year,role,owner,skills:[string]}], open_roles, my_role (owner/member/null), my_request (null or {id,role,status}), pending_requests, pending_invitations.
- Create input: title, description, category, course, cover_url, skills [string], owner_role, roles [{name,spots}], max_size, deadline, duration, meeting, accepting. Empty optional fields are sent as empty strings.
- Request: id, type (received/invitation/sent), kind (request/invitation), status, role, message, created_at, project {id,title,open_spots}, student, by (student brief or null), match.
- Recommendation: id, name, major, year, match, fits, invited, skills [[name,matchedBoolean]].
- Notification: id, kind, text, created_at, unread; request_id when actionable.
- Admin overview: stats {students,projects,teams,reports,deltas}, activity [{week,requests,projects}], categories [{name,count}], reports [{id,project,owner,reason,reporters,created_at,status}], users [{id,name,major,year,email,student_id,role,status,projects}].

## Server rules still required

Enforce ownership, membership, admin authorization, suspension, allowed roles, capacity, duplicate request prevention and atomic acceptance on the server. Reject remaining pending requests/invitations when a team becomes full. Protect PII in student/admin responses. Frontend route guards and mock logic are not security boundaries. Admin visibility currently accepts Cognito `admin` group OR profile role `admin`; the backend must enforce the agreed authoritative policy, recommended Cognito admin group, regardless of UI visibility.
