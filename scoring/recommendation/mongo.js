import { MongoClient } from "mongodb";

export const uri =
    "mongodb://admin:admin@203.113.132.140:8000/?authSource=admin";
export const DB_NAME = "mydb";

export async function getDb() {
    const client = new MongoClient(uri);
    await client.connect();
    return { db: client.db(DB_NAME), client };
}
