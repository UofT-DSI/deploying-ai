#!/usr/bin/env python3
"""
One-time setup script to create and populate the ChromaDB collection
with Caribbean pirate tales/stories data. Run the below command before starting the app.

python -m assignment_chat.setup_tales_data
"""
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from dotenv import load_dotenv
import os

load_dotenv(".env")
load_dotenv(".secrets")

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_data")
COLLECTION_NAME = "caribbean_tales"

# Note: I used an LLM to generate this data to make it more interesting and varied for users
CARIBBEAN_TALES = [
    # === Famous Pirates ===
    "Blackbeard, whose real name was Edward Teach, was the most feared pirate of the Golden Age of Piracy. He sailed aboard the Queen Anne's Revenge and was known for weaving slow-burning fuses into his thick black beard during battle, creating a demonic halo of smoke around his face. He blockaded the port of Charleston, South Carolina in 1718 and terrorized the Atlantic coast before being killed in a fierce battle off the coast of North Carolina.",

    "Anne Bonny was one of the most famous female pirates in history. Born in Ireland around 1697, she left her husband to sail with the pirate Calico Jack Rackham. She was known for her fierce temper and skill in combat, fighting alongside the crew in men's clothing. When Calico Jack was captured, Anne reportedly told him: 'Had you fought like a man, you need not have been hanged like a dog.'",

    "Calico Jack Rackham earned his nickname from the colorful calico clothing he wore. He captained a sloop in the Caribbean and is famous for having two women pirates on his crew: Anne Bonny and Mary Read. His Jolly Roger flag, featuring a skull with crossed swords, became one of the most iconic pirate symbols in history.",

    "Henry Morgan was a Welsh privateer who became one of the most successful and ruthless buccaneers in Caribbean history. He sacked Panama City in 1671, crossing the Isthmus of Panama with over a thousand men. Despite his piracy, he was knighted by King Charles II and appointed Lieutenant Governor of Jamaica, dying wealthy and respected in 1688.",

    "Mary Read disguised herself as a man for most of her life, first serving in the British military before turning to piracy. She sailed with Calico Jack Rackham and Anne Bonny, and was known for being an exceptionally fierce fighter. Like Anne Bonny, she was captured in 1720 but escaped execution by claiming to be pregnant.",

    "Bartholomew Roberts, known as Black Bart, was the most successful pirate of the Golden Age, capturing over 400 ships. He was known for his strict pirate code, which included rules about gambling, lights-out times, and keeping weapons clean. Unusually for a pirate, he preferred tea over rum and dressed in fine crimson clothing.",

    "Sir Francis Drake was an English sea captain and privateer who circumnavigated the globe between 1577 and 1580. The Spanish called him 'El Draque' and feared him greatly. He plundered Spanish ports and treasure ships throughout the Caribbean, amassing enormous wealth for himself and Queen Elizabeth I.",

    "Charles Vane was a notoriously cruel English pirate who operated in the Caribbean during the early 18th century. He refused the King's pardon offered at Nassau and continued his piracy until his own crew, led by Calico Jack Rackham, voted him out as captain for cowardice during an encounter with a French warship.",

    # === Legendary Locations ===
    "Tortuga, officially Ile de la Tortue, was the pirate capital of the Caribbean during the 17th century. Located off the northwest coast of Hispaniola, it served as a haven for buccaneers, smugglers, and outlaws of every nation. Its natural harbor provided shelter for pirate ships, and its lawless taverns were legendary for rum, gambling, and brawls that could last for days.",

    "Port Royal, Jamaica was once called 'the wickedest city on Earth.' In the late 1600s, it was the center of Caribbean commerce and piracy, with more bars per square foot than any city in the world. The city was destroyed by a massive earthquake on June 7, 1692, when two-thirds of it sank into the sea, which many considered divine punishment for its sinful ways.",

    "Nassau in the Bahamas became the Republic of Pirates from 1706 to 1718, when pirates including Blackbeard, Charles Vane, and Calico Jack established a lawless stronghold there. The harbor was too shallow for large warships but perfect for pirate sloops. It ended when Woodes Rogers arrived as the new governor with a royal pardon and a fleet of warships.",

    "The Spanish Main referred to the mainland coastline of the Spanish Empire around the Caribbean Sea, stretching from Mexico to Venezuela. It was the route for Spanish treasure fleets carrying gold, silver, and emeralds from the New World back to Spain, making it the prime hunting ground for every pirate and privateer in the Caribbean.",

    "Isla de la Juventud (Isle of Youth), located south of Cuba, is believed by many to be the inspiration for Treasure Island in Robert Louis Stevenson's famous novel. The island was a frequent hideout for pirates including Francis Drake and Henry Morgan, and local legends claim that vast pirate treasures remain buried in its caves and jungles.",

    "The Bermuda Triangle, stretching between Miami, Bermuda, and Puerto Rico, has been the subject of mystery for centuries. Sailors in the Age of Piracy reported strange compass readings, sudden storms that appeared from nowhere, and ships that vanished without a trace. Some believed the area was cursed by ancient sea gods or guarded by enormous sea serpents.",

    "Shipwreck Cove is a legendary gathering place spoken of in pirate lore where the Brethren Court of pirate lords would convene to discuss matters affecting all pirates. Hidden in a remote inlet surrounded by the hulls of wrecked ships, it was said to be accessible only to those who knew the secret approach through treacherous reef passages.",

    # === Legendary Ships ===
    "The Queen Anne's Revenge was Blackbeard's flagship, originally a French slave ship called La Concorde that Blackbeard captured in 1717. He mounted 40 cannons on the vessel, making it one of the most powerful pirate ships in the Caribbean. The wreck was discovered off the coast of North Carolina in 1996, and artifacts including cannons, anchors, and gold dust have been recovered.",

    "The Whydah Gally was a fully rigged galley ship originally built for the slave trade. Pirate captain Black Sam Bellamy captured it in 1717 and it became his flagship. The Whydah carried treasure from over 50 captured ships before sinking in a storm off Cape Cod. It was the first verified pirate shipwreck ever discovered, yielding over 200,000 artifacts.",

    "The Black Pearl is the legendary pirate ship said to be the fastest vessel in the Caribbean. According to pirate lore, the ship was once called the Wicked Wench before being burned and sunk, only to be raised from the depths through a dark bargain. With its distinctive black sails and hull, the Pearl could outrun any ship in the Royal Navy and was said to be nigh uncatchable.",

    "The Flying Dutchman is a legendary ghost ship doomed to sail the oceans forever, never able to make port. Sightings of the phantom vessel have been reported by sailors for centuries, particularly near the Cape of Good Hope. According to Caribbean lore, the Dutchman ferries the souls of those who die at sea to the afterlife, captained by a cursed soul bound to the ship for eternity.",

    # === Sea Myths and Legends ===
    "The Kraken is a legendary sea monster of enormous size said to dwell in the deepest waters of the Caribbean and the North Atlantic. Described as a massive creature with tentacles that could wrap around an entire ship and drag it to the ocean floor, the Kraken was the most feared creature of the deep. Sailors believed that disturbing certain cursed waters would awaken the beast.",

    "Davy Jones' Locker is the maritime term for the bottom of the ocean, the final resting place of drowned sailors and sunken ships. Davy Jones himself was said to be the devil of the sea, a supernatural figure who collected the souls of dead pirates and kept them in a locker at the bottom of the ocean. His name was invoked as a curse among seafarers.",

    "Caribbean mermaids, unlike the gentle sirens of European lore, were said to be dangerous and cunning creatures who lured sailors with beautiful singing voices before dragging them beneath the waves. Island fishermen reported seeing them basking on rocks near Dominica and Trinidad, and many believed they guarded underwater caverns filled with sunken treasure.",

    "The Fountain of Youth was believed to exist somewhere in the Caribbean or Florida. Spanish explorer Juan Ponce de Leon searched for it in 1513. Pirates and explorers alike sought this legendary spring whose waters could restore youth and grant immortality. Many expeditions were launched from Caribbean ports, though none ever confirmed finding the fountain.",

    "The legend of cursed Aztec gold tells of a stone chest containing 882 identical gold pieces that were plundered from the Aztec Empire. According to the curse, anyone who removed a piece from the chest would be condemned to an undead existence, unable to feel pleasure or pain, appearing as a living skeleton in moonlight. Only by returning every last piece could the curse be broken.",

    "Will-o'-the-wisps, known as 'Jack o' Lanterns' by Caribbean sailors, were mysterious glowing lights seen hovering over swamps and shallow coastal waters at night. Pirates believed these lights were the spirits of dead buccaneers guarding their buried treasure, leading greedy treasure hunters deeper into dangerous swamps where they would become hopelessly lost.",

    # === Cursed Treasures and Artifacts ===
    "The Dead Man's Chest is said to be an indestructible chest forged from the timbers of a cursed ship. According to legend, the chest contains the still-beating heart of Davy Jones himself, cut out and locked away as the price of his immortality. Whoever possesses the chest controls the Flying Dutchman and commands the creatures of the deep.",

    "Captain Kidd's treasure is one of the most sought-after pirate hoards in history. William Kidd, a Scottish privateer turned pirate, was said to have buried enormous treasure somewhere in the Caribbean or along the eastern seaboard before his capture in 1699. Despite centuries of searching, the bulk of his treasure has never been found, spawning countless treasure hunts and legends.",

    "The Pieces of Eight were Spanish silver dollar coins that served as the primary currency of the Caribbean pirate economy. Worth eight Spanish reals each, they could literally be cut into eight wedge-shaped pieces called bits to make change. The expression 'two bits' meaning a quarter comes from this practice. Pirates hoarded these coins in great quantities.",

    "The Compass of Confused Directions is a legendary artifact whispered about in the most disreputable taverns of the Caribbean. Said to have been crafted by a confused sea witch off the coast of Trinidad who could not decide between rum and treasure, this compass always points to what the holder wants second-most. It is utterly useless for navigation and absolutely priceless as a curiosity.",

    # === Caribbean History and Pirate Life ===
    "The Golden Age of Piracy lasted roughly from 1650 to 1730 and was centered in the Caribbean. During this period, thousands of pirates roamed the seas, preying on merchant ships and Spanish treasure fleets. The era was fueled by colonial rivalries between England, Spain, France, and the Netherlands, with each nation sometimes sponsoring pirates to attack their enemies' shipping.",

    "The Pirate Code, or Articles of Agreement, was a set of rules that governed life aboard pirate ships. Contrary to popular belief, pirate ships were among the most democratic institutions of their time. Captains were elected by the crew and could be voted out. The code covered everything from the division of plunder to compensation for injuries to the prohibition of gambling aboard ship.",

    "Grog was the standard drink aboard pirate ships, made by mixing rum with water and sometimes adding lime or lemon juice. The addition of citrus helped prevent scurvy, though pirates did not understand the science behind it. A daily ration of grog was considered a right, and any captain who withheld it risked mutiny from his crew.",

    "Walking the plank is a popular image of pirate punishment, but historical evidence suggests it was rarely practiced. More common punishments included marooning, where a pirate was left on a deserted island with a pistol containing a single shot, or keelhauling, where the offender was dragged under the ship's hull. Flogging and being put in irons were everyday disciplinary measures.",

    "Pirate flags, collectively known as Jolly Rogers, were designed to terrify merchant ships into surrendering without a fight. Each pirate captain had a unique flag. Blackbeard's showed a skeleton stabbing a heart, Calico Jack's featured crossed swords, and Bartholomew Roberts' depicted himself standing on two skulls. A red flag meant no quarter would be given.",

    "Letters of Marque were official documents issued by governments that authorized private ship captains to attack and plunder enemy vessels during wartime. These privateers were considered legal combatants rather than pirates. Many famous pirates, including Henry Morgan and Francis Drake, began their careers as legitimate privateers before crossing the line into outright piracy.",

    "The Brethren Court was a legendary council of the nine most powerful pirate lords in the Caribbean. According to pirate tradition, the Court could only be called by ringing the bells of the ancient Pirate Temple on Shipwreck Island. Their most famous decree was the binding of the sea goddess Calypso in human form, a decision that forever changed the balance of power on the seas.",

    # === Islands and Hidden Places ===
    "Dominica, known as the Nature Island of the Caribbean, is one of the most rugged and volcanic islands in the Lesser Antilles. Its dense rainforests, boiling lakes, and hidden waterfalls made it a perfect hiding place for pirates. The indigenous Kalinago people, who still inhabit the island, told stories of underwater caves accessible only at low tide that once held pirate treasure.",

    "The Blue Hole of Belize is a giant underwater sinkhole over 300 meters across and 125 meters deep, located in the center of Lighthouse Reef Atoll. Ancient Mayan legends warned that it was a gateway to the underworld, and pirates believed that a great sea serpent dwelled in its depths. The hole's perfect circular shape and dark blue water made it a landmark for Caribbean navigators.",

    "Rum Cay in the Bahamas was a favorite watering hole for pirates traveling between Nassau and the Spanish Main. The island got its name from a shipwreck that spilled barrels of rum onto the beach, creating a legendary free-for-all that attracted pirates from across the Caribbean. The island's caves were rumored to contain hidden stashes of treasure left by crews who never returned.",

    "Nevis, a small volcanic island in the Lesser Antilles, was where Alexander Hamilton was born and where many pirates came to careen their ships. The island's steep volcanic slopes and remote beaches provided cover from the Royal Navy. Local legend tells of a pirate captain who buried his treasure inside a lava tube on the side of Nevis Peak, sealing the entrance with gunpowder.",

    # === More Myths ===
    "Sea turtles were considered sacred by Caribbean pirates, who believed that the oldest turtles carried the memories of the ocean on their shells. It was considered extremely bad luck to harm a sea turtle that approached your ship willingly. Some pirates carved maps and coordinates into turtle shells as a way of hiding treasure locations in plain sight.",

    "The Sargasso Sea, a region of the North Atlantic bounded by ocean currents, was feared by Caribbean sailors for its vast floating mats of sargassum seaweed that could trap becalmed ships for weeks. Pirates told tales of entire ghost fleets trapped in the weed, their crews long dead, their treasure holds still full of gold and jewels waiting to be claimed by anyone brave enough to venture in.",

    "According to Caribbean legend, the constellation known as the Southern Cross was placed in the sky by the sea goddess Calypso to guide lost sailors home. Pirates who could navigate by the Southern Cross were said to have Calypso's blessing and would never be lost at sea. However, those who offended the goddess would find the stars hidden behind eternal clouds.",
]

TALES_METADATA = [
    {"category": "famous_pirates"}, {"category": "famous_pirates"},
    {"category": "famous_pirates"}, {"category": "famous_pirates"},
    {"category": "famous_pirates"}, {"category": "famous_pirates"},
    {"category": "famous_pirates"}, {"category": "famous_pirates"},
    {"category": "locations"}, {"category": "locations"},
    {"category": "locations"}, {"category": "locations"},
    {"category": "locations"}, {"category": "locations"},
    {"category": "locations"},
    {"category": "ships"}, {"category": "ships"},
    {"category": "ships"}, {"category": "ships"},
    {"category": "myths"}, {"category": "myths"},
    {"category": "myths"}, {"category": "myths"},
    {"category": "myths"}, {"category": "myths"},
    {"category": "treasures"}, {"category": "treasures"},
    {"category": "treasures"}, {"category": "treasures"},
    {"category": "history"}, {"category": "history"},
    {"category": "history"}, {"category": "history"},
    {"category": "history"}, {"category": "history"},
    {"category": "history"},
    {"category": "locations"}, {"category": "locations"},
    {"category": "locations"}, {"category": "locations"},
    {"category": "myths"}, {"category": "myths"},
    {"category": "myths"},
]


def setup_chromadb():
    print(f"Setting up ChromaDB at {CHROMA_PATH}...")

    embedding_function = OpenAIEmbeddingFunction(
        api_key="any value",
        api_base='https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1',
        model_name="text-embedding-3-small",
        default_headers={"x-api-key": os.getenv('API_GATEWAY_KEY')}
    )

    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

    # delete collection if it exists (required while iterating during testing)  
    existing_collections = [c.name for c in chroma_client.list_collections()]
    
    if COLLECTION_NAME in existing_collections:
        print(f"Deleting existing collection: {COLLECTION_NAME}")
        chroma_client.delete_collection(name=COLLECTION_NAME)

    collection = chroma_client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function
    )

    ids = [f"tale_{i}" for i in range(len(CARIBBEAN_TALES))]

    print(f"Adding {len(CARIBBEAN_TALES)} tale entries to collection...")

    collection.add(
        documents=CARIBBEAN_TALES,
        ids=ids,
        metadatas=TALES_METADATA
    )

    print(f"Collection '{COLLECTION_NAME}' created with {collection.count()} documents.")
    print("ChromaDB setup complete")


if __name__ == "__main__":
    setup_chromadb()
