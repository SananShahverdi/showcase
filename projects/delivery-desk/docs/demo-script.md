# Demo script

1. Start the app (`npm start` from the portfolio root, then open Delivery Desk) and show the empty board.
2. Click **Add sample tasks** to load six tasks across two projects. Click it again to show nothing is duplicated.
3. Filter by project **Customer portal** and priority **High**, then search for `invoice`.
4. Open a task, change its stage and due date, and save. Show the history panel listing each field's before and after value.
5. Open the same task in a second tab. Save a change in the first tab, then try to save in the second: the app refuses with a clear message instead of overwriting.
6. Stop and restart the server, reload the page, and show that tasks and history are still there.
