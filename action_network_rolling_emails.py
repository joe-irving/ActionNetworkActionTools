from action_network import ActionNetwork
from dotenv import load_dotenv
import os
import pyairtable as airtable

load_dotenv()

class RollingEmailer():
    def __init__(self, trigger_tag_id, target_view, message_view, prefix, end_tag_id, an_key="ACTION_NETWORK_API", airtable_key="AIRTABLE_API_KEY"):
        self.an = ActionNetwork(key = os.environ.get(an_key))
        self.trigger_tag_id = trigger_tag_id
        self.airtable_base = os.environ.get("AIRTABLE_BASE")
        self.airtable_target_table = os.environ.get("AIRTABLE_TARGET_TABLE")
        self.airtable_target_view = target_view
        self.airtable_message_table = os.environ.get("AIRTABLE_MESSAGE_TABLE")
        self.airtable_message_view = message_view
        self.prefix = prefix
        self.end_tag_id = end_tag_id
        self.airtable = airtable.Api(os.environ.get(airtable_key))
    
    def process(self):
        taggings = self.new_taggings()
        print(f"Processing {len(taggings)} new taggings.")
        people = self.new_people(taggings)
        for person in people:
           self.assign_target(person)
        self.delete_taggings(taggings)
        print("Processing done.")
        return len(people)
    
    def new_taggings(self):
        taggings = self.an.get_all(f"tags/{self.trigger_tag_id}/taggings")
        return taggings        

    def new_people(self, taggings):
        people = [self.an.get("people", tagging["person_id"]) for tagging in taggings]
        return people
    
    def delete_taggings(self, taggings):
        for tagging in taggings:
            self.an._delete(tagging["_links"]["self"]["href"])
    
    def assign_target(self, person):
        if person["custom_fields"]:
            if person["custom_fields"].get(f"{self.prefix}_target_index"):
                target_index = int(person["custom_fields"].get(f"{self.prefix}_target_index"))
            else:
                target_index = 0
        else:
            target_index = 0
        # Get next target in view
        target = self.airtable.all(self.airtable_base, self.airtable_target_table, view=self.airtable_target_view, max_records=1)[0]
        # Get next message in view
        messages = self.airtable.all(
            self.airtable_base,
            self.airtable_message_table,
            view=self.airtable_message_view,
            formula=f"OR({{Pin}}=TRUE(), {{Previous Emails}}={target_index})"
            )
        message = "" if len(messages) == 0 else messages[0]['fields'].get('HTML Content')
        # Create object to update person with prefix
        update = {
            "next_email": target['fields'].get('Email'),
            "next_first_name": target['fields'].get('First Name'),
            "next_last_name": target['fields'].get('Last Name'),
            "next_position": target['fields'].get('Position'),
            "next_phone": target['fields'].get('Phone'),
            "next_message": message,
            "target_index": target_index + 1
        }
        # update person
        person_updated = self.an.put(f"people/{person['id']}", json=self._make_person_update(update)).json()
        # Update target on airtable
        contacts_sent_to = list(target['fields'].get('Contact Sent To')) if target['fields'].get('Contact Sent To') else []
        contacts_sent_to.append(person["_links"]["self"]["href"])
        self.airtable.update(self.airtable_base, self.airtable_target_table, target['id'], {
            "Emails Sent Manual": int(target['fields'].get('Emails Sent Manual')) + 1,
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
    

if __name__ == "__main__":
    pass
    