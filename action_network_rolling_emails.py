from action_network import ActionNetwork
from dotenv import load_dotenv
import os
import pyairtable as airtable
from datetime import datetime

load_dotenv()


class RollingEmailer():
    def __init__(self, trigger_tag_id, target_view, message_view, prefix, end_tag_id, an_key="ACTION_NETWORK_API", airtable_key="AIRTABLE_API_KEY", targets_each=1, delay_mins=0):
        self.an = ActionNetwork(key=os.environ.get(an_key))
        self.trigger_tag_id = trigger_tag_id
        self.airtable_base = os.environ.get("AIRTABLE_BASE")
        self.airtable_target_table = os.environ.get("AIRTABLE_TARGET_TABLE")
        self.airtable_target_view = target_view
        self.airtable_message_table = os.environ.get("AIRTABLE_MESSAGE_TABLE")
        self.airtable_message_view = message_view
        self.prefix = prefix
        self.end_tag_id = end_tag_id
        self.airtable = airtable.Api(os.environ.get(airtable_key))
        self.targets_each = targets_each
        self.delay_mins = delay_mins

    def log(self, text):
        print(f"{self.prefix}: {text}")

    def process(self):
        taggings = self.new_taggings()
        processed_taggings = []
        self.log(f"Processing {len(taggings)} new taggings.")
        people = self.new_people(taggings)
        for i in range(len(people)):
            tagging = taggings[i]
            target_index = self._get_target_index(people[i])
            difference = datetime.now() - \
                datetime.strptime(
                    tagging['modified_date'], '%Y-%m-%dT%H:%M:%SZ')
            if target_index == 0 or (difference.total_seconds() / 60) > self.delay_mins:
                self.assign_target(people[i])
                self.an._delete(tagging["_links"]["self"]["href"])
                processed_taggings.append(tagging)
        # self.delete_taggings(taggings)
        self.log(
            f"Processing complete for {len(processed_taggings)} taggings.")
        return len(people)

    def new_taggings(self):
        taggings = self.an.get_all(f"tags/{self.trigger_tag_id}/taggings")
        return taggings

    def new_people(self, taggings):
        people = [self.an.get("people", tagging["person_id"])
                  for tagging in taggings]
        return people

    def delete_taggings(self, taggings):
        for tagging in taggings:
            self.an._delete(tagging["_links"]["self"]["href"])

    def assign_target(self, person):
        self.current_person = person
        target_index = self._get_target_index(person)
        # Get next target in view
        target = self._get_target()
        # Get next message in view
        messages = self.airtable.all(
            self.airtable_base,
            self.airtable_message_table,
            view=self.airtable_message_view,
            formula=f"OR({{Pin}}=TRUE(), {{Previous Emails}}={target_index})"
        )
        message = "" if len(
            messages) == 0 else messages[0]['fields'].get('HTML Content')
        # Create object to update person with prefix
        update = {
            "next_email": target['email'],
            "next_first_name": target['first_name'],
            "next_last_name": target['last_name'],
            "next_position": target['position'],
            "next_phone": target['phone'],
            "next_message": message,
            "target_index": target_index + 1
        }
        # update person
        person_updated = self.an.put(
            f"people/{person['id']}", json=self._make_person_update(update)).json()
        # Update target on airtable
        for at_target in self.targets:
            contacts_sent_to = list(at_target['fields'].get(
                'Contact Sent To')) if at_target['fields'].get('Contact Sent To') else []
            contacts_sent_to.append(person["_links"]["self"]["href"])
            self.airtable.update(self.airtable_base, self.airtable_target_table, at_target['id'], {
                "Emails Sent Manual": int(at_target['fields'].get('Emails Sent Manual')) + 1,
                "Contact Sent To": contacts_sent_to
            }, typecast=True)
        # add end tag
        self.an.post(f"tags/{self.end_tag_id}/taggings", json={
            "_links": {
                "osdi:person": {
                    "href": person["_links"]["self"]["href"]
                }
            }
        })
        return person_updated

    def _make_person_update(self, update):
        person_update = {
            "custom_fields": {}
        }
        for key in update:
            person_update["custom_fields"][f"{self.prefix}_{key}"] = update[key]
        return person_update

    def _get_target(self):
        self.targets = self.airtable.all(self.airtable_base, self.airtable_target_table,
                                         view=self.airtable_target_view, max_records=self.targets_each)
        target_list = {
            "email": [],
            "first_name": [],
            "last_name": [],
            "position": [],
            "phone": []
        }

        target_output = {}

        for target in self.targets:
            target_list["email"].append(str(target['fields'].get('Email')))
            target_list["first_name"].append(str(target['fields'].get(
                'First Name')))
            target_list["last_name"].append(
                str(target['fields'].get('Last Name')))
            target_list["phone"].append(str(target['fields'].get('Phone')))
            target_list["position"].append(
                str(target['fields'].get('Position')))

        for key in target_list:
            target_output[key] = ", ".join(target_list[key])

        return target_output

    def _get_target_index(self, person):
        if person["custom_fields"]:
            if person["custom_fields"].get(f"{self.prefix}_target_index"):
                target_index = int(person["custom_fields"].get(
                    f"{self.prefix}_target_index"))
            else:
                target_index = 0
        else:
            target_index = 0
        return target_index


if __name__ == "__main__":
    pass
